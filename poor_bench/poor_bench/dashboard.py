import json
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output, dash_table
import re
#from llm_manager import LLMManager

def load_results(file_path):
    """Load and parse the JSON results file."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    return data['results']

def load_llms(llm_file_path):
    """Load LLM configurations from JSON."""
    with open(llm_file_path, 'r') as f:
        data = json.load(f)
    return data['llms']

def process_data(results):
    """Convert results to a DataFrame and extract test categories."""
    records = []
    for model, tests in results.items():
        for test in tests:
            test_category = re.match(r'(\w+)_', test['test_id']).group(1)
            # Parse model for display
            try:
                provider, name, think_str = model.split(":", 2)
                display_model = f"{provider}:{name} (Think: {think_str})"
            except ValueError:
                display_model = model  # Fallback for legacy format
            records.append({
                'model': display_model,
                'model_id': model,  # Store original ID for filtering
                'test_id': test['test_id'],
                'score': test['score'],
                'details': test['details'],
                'response': test['response'],
                'timestamp': test['timestamp'],
                'execution_time_ms': test['execution_time_ms'],
                'test_category': test_category,
                'think': test.get('think', False)
            })
    return pd.DataFrame(records)

def compute_model_totals(df, llms):
    """Compute totals for model comparison (number of tests, average score, pass rate, average execution time, size)."""
    totals = df.groupby('model_id').agg(
        total_tests=('test_id', 'count'),
        avg_score=('score', 'mean'),
        pass_count=('score', lambda x: (x == 1.0).sum()),
        avg_execution_time=('execution_time_ms', 'mean'),
        think_enabled=('think', lambda x: 0 if x.sum()==0 else 1)
    ).reset_index()
    totals['pass_rate'] = (totals['pass_count'] / totals['total_tests'] * 100).round(2)
    totals['avg_score'] = totals['avg_score'].round(2)
    totals['avg_execution_time'] = (totals['avg_execution_time'] / 1000).round(1)
    # Add model size
    llm_sizes = {f"{llm['provider']}:{llm['name']}:{'true' if llm.get('parameters', {}).get('think', False) else 'false'}": llm['size'] for llm in llms}
    totals['size'] = totals['model_id'].map(llm_sizes).fillna(0.0)
    # Create display model name
    totals['model'] = totals['model_id'].apply(
        lambda x: f"{x.split(':')[0]}:{x.split(':')[1]} (Think: {x.split(':')[2]})" if len(x.split(':')) == 3 else x
    )
    return totals[['model', 'model_id', 'total_tests', 'avg_score', 'pass_rate', 'avg_execution_time', 'think_enabled', 'size']]

def detect_issues(df):
    """Identify potential issues in test results (e.g., score 0.0 or unexpected formats)."""
    issues = []
    for _, row in df.iterrows():
        if row['score'] == 0.0:
            issues.append(f"Test {row['test_id']} (Model: {row['model']}) failed with score 0.0. Details: {row['details']}")
        if '{' in row['response'] and row['test_category'] in ['math_problems', 'sentiment_analysis']:
            issues.append(f"Test {row['test_id']} (Model: {row['model']}) has unexpected JSON object format in response: {row['response'][:100]}...")
    return issues

def create_dashboard(file_path, llm_file_path='llms.json'):
    """Create and run the Dash dashboard."""
    app = Dash(__name__)
    
    # Load and process data
    results = load_results(file_path)
    llms = load_llms(llm_file_path)
    df = process_data(results)
    
    # Get unique models for dropdown
    models = df['model_id'].unique().tolist()
    model_display_map = {row['model_id']: row['model'] for _, row in df[['model_id', 'model']].drop_duplicates().iterrows()}
    
    # Compute model totals for comparison
    model_totals = compute_model_totals(df, llms)
    
    # Layout
    app.layout = html.Div([
        html.H1("LLM Benchmarking Dashboard", style={'textAlign': 'center'}),
        html.Label("Select LLM Model:"),
        dcc.Dropdown(
            id='model-dropdown',
            options=[{'label': model_display_map[model], 'value': model} for model in models],
            value=models[0],
            style={'width': '50%', 'margin': 'auto'}
        ),
        html.Br(),
        dcc.Graph(id='score-bar-chart'),
        html.H3("Model Comparison Plot"),
        dcc.Graph(id='model-comparison-plot'),
        html.H3("Test Results Table"),
        dash_table.DataTable(
            id='results-table',
            columns=[
                {'name': 'Test ID', 'id': 'test_id'},
                {'name': 'Score', 'id': 'score'},
                {'name': 'Test Category', 'id': 'test_category'},
                {'name': 'Execution Time (ms)', 'id': 'execution_time_ms'},
                {'name': 'Details', 'id': 'details', 'presentation': 'markdown'},
                {'name': 'Think Enabled', 'id': 'think'},
            ],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'minWidth': '100px', 'maxWidth': '300px', 'whiteSpace': 'normal'},
            page_size=10,
        ),
        html.H3("Potential Issues"),
        html.Div(id='issues-text', style={'whiteSpace': 'pre-line', 'padding': '10px'}),
        html.H3("Model Comparison"),
        dash_table.DataTable(
            id='model-comparison-table',
            columns=[
                {'name': 'Model', 'id': 'model', 'type': 'text'},
                {'name': 'Total Tests', 'id': 'total_tests', 'type': 'numeric'},
                {'name': 'Average Score', 'id': 'avg_score', 'type': 'numeric'},
                {'name': 'Pass Rate (%)', 'id': 'pass_rate', 'type': 'numeric'},
                {'name': 'Avg Execution Time (s)', 'id': 'avg_execution_time', 'type': 'numeric'},
                {'name': 'Think Enabled', 'id': 'think_enabled', 'type': 'numeric'},
                {'name': 'Size (B)', 'id': 'size', 'type': 'numeric'},
            ],
            data=model_totals.to_dict('records'),
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'minWidth': '100px'},
            sort_action='native',  # Enable interactive sorting
            sort_mode='single',    # Allow sorting by one column at a time
        ),
        html.Button("Refresh Analysis", id='refresh-button', n_clicks=0),
    ], style={'padding': '20px'})
    
    # Callbacks
    @app.callback(
        [
            Output('score-bar-chart', 'figure'),
            Output('results-table', 'data'),
            Output('issues-text', 'children'),
            Output('model-comparison-table', 'data'),
            Output('model-comparison-plot', 'figure')
        ],
        [Input('model-dropdown', 'value'), Input('refresh-button', 'n_clicks')]
    )
    def update_dashboard(selected_model, n_clicks):
        # Reload and reprocess data for refresh
        results = load_results(file_path)
        llms = load_llms(llm_file_path)
        df = process_data(results)
        model_totals = compute_model_totals(df, llms)
        
        # Filter data for selected model
        model_df = df[df['model_id'] == selected_model]
        
        # Create bar chart
        fig = px.bar(
            model_df,
            x='test_id',
            y='score',
            color='test_category',
            title=f'Scores by Test ID for {model_df["model"].iloc[0] if not model_df.empty else selected_model}',
            labels={'test_id': 'Test ID', 'score': 'Score (0.0-1.0)', 'test_category': 'Test Category'},
            height=400
        )
        fig.update_layout(xaxis_tickangle=45)
        
        # Create model comparison plot
        # Sort model_totals by size
        model_totals_sorted = model_totals.sort_values('size')
        comparison_fig = px.bar(
            model_totals_sorted,
            x='model',
            y='avg_score',
            title='Model Comparison: Average Score (Models Ordered by Size)',
            labels={'model': 'Model', 'avg_score': 'Average Score'},
            height=800,
            color='avg_score',
            color_continuous_scale='Blues'
        )
        comparison_fig.update_layout(
            xaxis_tickangle=45,
            yaxis_title='Average Score (0.0-1.0)',
            xaxis={'categoryorder': 'array', 'categoryarray': model_totals_sorted['model'].tolist()}
        )
        
        # Prepare table data
        table_data = model_df[['test_id', 'score', 'test_category', 'execution_time_ms', 'details', 'think']].to_dict('records')
        
        # Detect issues
        issues = detect_issues(model_df)
        issues_text = "No issues detected." if not issues else "\n".join(issues)
        
        return fig, table_data, issues_text, model_totals.to_dict('records'), comparison_fig
    
    return app

if __name__ == '__main__':
    # Use the provided JSON file path
    file_path = 'results.json'
    app = create_dashboard(file_path)
    app.run(debug=True)