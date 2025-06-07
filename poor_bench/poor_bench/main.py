import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional
from .llm_manager import LLMManager # Assuming llm_manager.py is in the same directory

# Ensure the package components can be imported if main.py is run directly
# For example, when `python poor_bench/main.py ...` is executed from `poor_ai/`
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
#PARENT_DIR = os.path.dirname(SCRIPT_DIR)
#sys.path.insert(0, PARENT_DIR) # Add poor_ai to path, so poor_bench is a known package
# Better: if poor_bench is installed or PYTHONPATH is set, direct imports work.
# For development, running `python -m poor_bench.main ...` from `poor_ai/` is preferred.

try:
    from .config_manager import ConfigManager
    from .llm_manager import LLMManager
    from .test_runner import TestRunner
    from .report_generator import ReportGenerator
except ImportError:
    # Fallback for direct script execution if not run as a module
    # This is hacky; proper packaging or PYTHONPATH setup is better.
    sys.path.insert(0, os.path.join(SCRIPT_DIR, '..')) # Assumes poor_bench is in poor_ai/
    from poor_bench.config_manager import ConfigManager
    from poor_bench.llm_manager import LLMManager
    from poor_bench.test_runner import TestRunner
    from poor_bench.report_generator import ReportGenerator


def run_tests_handler(args):
    base_path = args.config_dir if args.config_dir else None
    cm = ConfigManager(base_path=base_path)
    lm = LLMManager()
    runner = TestRunner(cm, lm)

    all_llm_configs = cm.load_llms().get("llms", [])
    target_llms_configs = []
    if args.llm == ["all"]:
        target_llms_configs = all_llm_configs
    else:
        for llm_id_str in args.llm:
            conf = cm.get_llm_config_by_id(llm_id_str)
            if conf:
                target_llms_configs.append(conf)
            else:
                print(f"Warning: LLM ID '{llm_id_str}' not found in llms.json. Skipping.")
    
    if not target_llms_configs:
        print("No valid LLMs specified or found. Exiting.")
        return

    all_tests_master_list = cm.load_tests().get("tests", [])
    tests_to_run_for_all_llms = []

    if args.test == ["all"]:
        tests_to_run_for_all_llms = all_tests_master_list
    else:
        for test_id_str in args.test:
            instance = cm.get_test_instance_by_id(test_id_str)
            if instance:
                tests_to_run_for_all_llms.append(instance)
            else:
                print(f"Warning: Test ID '{test_id_str}' not found in tests.json. Skipping.")
    
    # Further filter by class and level if specified
    if args.class_id:
        tests_to_run_for_all_llms = [t for t in tests_to_run_for_all_llms if t['class_id'] in args.class_id]
    if args.level is not None:
        tests_to_run_for_all_llms = [t for t in tests_to_run_for_all_llms if t['level'] == args.level]

    if not tests_to_run_for_all_llms:
        print("No tests selected after filtering. Exiting.")
        return

    print(f"Target LLMs: {[lm.llm_id(c) for c in target_llms_configs]}")
    print(f"Target Tests: {[t['test_id'] for t in tests_to_run_for_all_llms]}")

    tasks = []
    for llm_c in target_llms_configs:
        llm_id_str = lm.llm_id(llm_c)
        specific_tests_for_this_llm = tests_to_run_for_all_llms
        if not args.force:
            pending_test_instances = cm.get_pending_tests(llm_id_str, [t['test_id'] for t in tests_to_run_for_all_llms])
            pending_test_ids = {pt['test_id'] for pt in pending_test_instances}
            specific_tests_for_this_llm = [t for t in tests_to_run_for_all_llms if t['test_id'] in pending_test_ids]
            if not specific_tests_for_this_llm:
                print(f"No pending tests for LLM '{llm_id_str}' based on current selection. Use --force to re-run.")
                continue
        
        for test_instance in specific_tests_for_this_llm:
            tasks.append((runner, test_instance['test_id'], llm_id_str))

    if not tasks:
        print("No tasks to run after considering pending tests and filters. Exiting.")
        return

    print(f"\nStarting test execution for {len(tasks)} task(s)...")
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        futures = {executor.submit(r.run_test, tid, lid): (tid, lid) for r, tid, lid in tasks}
        for i, future in enumerate(as_completed(futures)):
            test_id, llm_id = futures[future]
            try:
                result = future.result()
                # Format llm_id for display
                try:
                    provider, name, think_str = LLMManager.split_llm_id(llm_id)
                    display_id = f"{provider}:{name} (Think: {think_str})"
                except ValueError:
                    display_id = llm_id
                print(f"({i+1}/{len(tasks)}) COMPLETED: Test '{test_id}' with LLM '{display_id}'. Score: {result['score']:.2f}")
            except Exception as e:
                print(f"({i+1}/{len(tasks)}) FAILED: Test '{test_id}' with LLM '{llm_id}'. Error: {e}")
    
    print("\nAll selected tests completed.")
    # Optionally, run a summary report after tests
    if args.auto_report:
        print("\nGenerating post-run summary report...")
        report_handler_args = argparse.Namespace(
            config_dir=args.config_dir, format='summary', output=None, 
            llm=[lm.llm_id(c) for c in target_llms_configs],
            test=[t['test_id'] for t in tests_to_run_for_all_llms]
        )
        report_handler(report_handler_args)

def report_handler(args):
    base_path = args.config_dir if args.config_dir else None
    cm = ConfigManager(base_path=base_path)
    rg = ReportGenerator(cm)

    llm_filter = args.llm if args.llm != ["all"] else None
    test_filter = args.test if args.test != ["all"] else None

    if args.format == 'summary':
        rg.generate_summary_report(llm_ids=llm_filter, test_ids=test_filter)
    elif args.format == 'csv':
        if not args.output:
            print("Error: --output filename is required for CSV format.")
            return
        rg.generate_csv_report(args.output, llm_ids=llm_filter, test_ids=test_filter)
    elif args.format == 'json':
        if not args.output:
            print("Error: --output filename is required for JSON format.")
            return
        rg.generate_json_report(args.output, llm_ids=llm_filter, test_ids=test_filter)
    else:
        print(f"Unknown report format: {args.format}")

def list_handler(args):
    base_path = args.config_dir if args.config_dir else None
    cm = ConfigManager(base_path=base_path)
    lm = LLMManager() # For consistent LLM ID generation

    if args.item == 'llms':
        llms_data = cm.load_llms().get("llms", [])
        if not llms_data: print("No LLMs configured.")
        for idx, llm_conf in enumerate(llms_data):
            llm_id = lm.llm_id(llm_conf)
            print(f"- {llm_id} (Provider: {llm_conf['provider']}, Endpoint: {llm_conf['endpoint']})")
    elif args.item == 'tests':
        tests_data = cm.load_tests().get("tests", [])
        if not tests_data: print("No tests configured.")
        for test in tests_data:
            print(f"- {test['test_id']} (Class: {test['class_id']}, Level: {test['level']})")
    elif args.item == 'classes':
        classes_data = cm.load_test_classes().get("test_classes", [])
        if not classes_data: print("No test classes configured.")
        for tc in classes_data:
            print(f"- {tc['id']}: {tc['description']}")
    else:
        print(f"Unknown item to list: {args.item}. Choose from 'llms', 'tests', 'classes'.")


def main():
    parser = argparse.ArgumentParser(description="Poor Bench: A lightweight LLM benchmarking framework.")
    parser.add_argument('--config-dir', type=str, help="Path to the directory containing config files (test_classes.yaml, etc.). Defaults to 'poor_bench' directory where main.py is located.")
    subparsers = parser.add_subparsers(dest='command', required=True, help='Sub-command help')

    # Run command
    run_parser = subparsers.add_parser('run', help='Run tests')
    run_parser.add_argument('--llm', type=str, nargs='+', default=['all'], help='LLM ID(s) (e.g., provider:name or provider:name:think) or "all"')
    run_parser.add_argument('--test', type=str, nargs='+', default=['all'], help='Test ID(s) or "all"')
    run_parser.add_argument('--class-id', type=str, nargs='+', help='Filter tests by class ID(s)')
    run_parser.add_argument('--level', type=int, help='Filter tests by difficulty level')
    run_parser.add_argument('--force', action='store_true', help='Re-run already completed tests')
    run_parser.add_argument('--max-workers', type=int, default=1, help='Maximum number of concurrent tests to run')
    run_parser.add_argument('--auto-report', action='store_true', help='Generate a summary report after tests complete for the run selection')
    run_parser.set_defaults(func=run_tests_handler)

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate reports')
    report_parser.add_argument('--format', type=str, choices=['summary', 'csv', 'json'], default='summary', help='Report format')
    report_parser.add_argument('--output', type=str, help='Output filename (for CSV/JSON formats)')
    report_parser.add_argument('--llm', type=str, nargs='+', default=['all'], help='Filter report by LLM ID(s) (e.g., provider:name:think) or "all"')
    report_parser.add_argument('--test', type=str, nargs='+', default=['all'], help='Filter report by Test ID(s) or "all"')
    report_parser.set_defaults(func=report_handler)

    # List command
    list_parser = subparsers.add_parser('list', help='List available configurations')
    list_parser.add_argument('item', type=str, choices=['llms', 'tests', 'classes'], help='Item to list')
    list_parser.set_defaults(func=list_handler)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
