import json
import csv
from typing import Dict, List, Any, Optional
import pandas as pd
import datetime

from .config_manager import ConfigManager

class ReportGenerator:
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager

    def _get_filtered_results(self, llm_ids: Optional[List[str]] = None, 
                             test_ids: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
        all_results_data = self.config_manager.load_results()
        raw_results_map = all_results_data.get("results", {})
        
        filtered_results_map = {}

        target_llm_ids = llm_ids if llm_ids else raw_results_map.keys()

        for llm_id_str, results_list in raw_results_map.items():
            if llm_id_str not in target_llm_ids:
                continue

            if not results_list:
                filtered_results_map[llm_id_str] = []
                continue
            
            if test_ids:
                current_llm_results = [res for res in results_list if res["test_id"] in test_ids]
            else:
                current_llm_results = list(results_list) # Make a copy
            
            if current_llm_results: # Add only if there are matching results
                 filtered_results_map[llm_id_str] = current_llm_results
        
        return filtered_results_map

    def generate_summary_report(self, llm_ids: Optional[List[str]] = None, 
                               test_ids: Optional[List[str]] = None) -> None:
        """Prints a summary report to the console."""
        results_map = self._get_filtered_results(llm_ids, test_ids)
        
        if not results_map:
            print("No results found for the given filters.")
            return

        print("\n--- Poor Bench Summary Report ---")
        for llm_id_str, results_list in results_map.items():
            if not results_list:
                print(f"\nLLM: {llm_id_str} - No results found.")
                continue

            total_tests = len(results_list)
            avg_score = sum(r["score"] for r in results_list) / total_tests if total_tests > 0 else 0
            avg_exec_time = sum(r["execution_time_ms"] for r in results_list) / total_tests if total_tests > 0 else 0
            think_enabled = sum(1 for r in results_list if r.get("think", False))
            
            # Parse llm_id_str for display
            try:
                provider, name, think_str = LLMManager.split_llm_id(llm_id_str)
                display_id = f"{provider}:{name} (Think: {think_str})"
            except ValueError:
                display_id = llm_id_str  # Fallback for legacy format
            
            print(f"\nLLM: {display_id}")
            print(f"  Total Tests Run: {total_tests}")
            print(f"  Average Score: {avg_score:.2f}")
            print(f"  Average Execution Time: {avg_exec_time:.0f} ms")
            print(f"  Tests with Think Enabled: {think_enabled}/{total_tests}")
            
            # Optional: Group by test class or level if that data is easily accessible/added to results
            # For now, a simple list of test scores:
            # print("  Individual Test Scores:")
            # for res in sorted(results_list, key=lambda x: x['test_id']):
            #     print(f"    - {res['test_id']}: {res['score']:.2f} ({res['execution_time_ms']}ms)")
        print("\n--- End of Report ---")

    def generate_csv_report(self, output_file: str, llm_ids: Optional[List[str]] = None, 
                           test_ids: Optional[List[str]] = None) -> None:
        """Generates a CSV report and saves it to output_file."""
        results_map = self._get_filtered_results(llm_ids, test_ids)
        
        if not results_map:
            print(f"No results to write to CSV for file {output_file}.")
            # Create an empty CSV with headers if desired, or just do nothing
            # with open(output_file, 'w', newline='', encoding='utf-8') as f:
            #    writer = csv.writer(f)
            #    writer.writerow(["llm_id", "test_id", "score", "execution_time_ms", "timestamp", "details", "response"])
            return

        report_data = []
        for llm_id_str, results_list in results_map.items():
            for result in results_list:
                report_data.append({
                    "llm_id": llm_id_str,
                    "test_id": result["test_id"],
                    "score": result["score"],
                    "execution_time_ms": result["execution_time_ms"],
                    "timestamp": result["timestamp"],
                    "details": result["details"],
                    "response": result["response"],
                    "think": result.get("think", False)
                })
        
        if not report_data:
            print(f"No data rows to write for CSV report {output_file}.")
            return

        try:
            df = pd.DataFrame(report_data)
            df.to_csv(output_file, index=False, encoding='utf-8')
            print(f"CSV report generated: {output_file}")
        except Exception as e:
            print(f"Error generating CSV report: {e}")

    def generate_json_report(self, output_file: str, llm_ids: Optional[List[str]] = None, 
                            test_ids: Optional[List[str]] = None) -> None:
        """Generates a JSON report (essentially filtered results.json) and saves it."""
        results_map = self._get_filtered_results(llm_ids, test_ids)
        
        report_content = {
            "version": self.config_manager.load_results().get("version", "1.0"), # Use original version
            "report_generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "filters_applied": {
                "llm_ids": llm_ids,
                "test_ids": test_ids
            },
            "results": results_map
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_content, f, indent=2)
            print(f"JSON report generated: {output_file}")
        except Exception as e:
            print(f"Error generating JSON report: {e}")