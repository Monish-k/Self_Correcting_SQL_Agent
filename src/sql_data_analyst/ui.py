from __future__ import annotations

import gradio as gr

from .agent import SQLAgent
from .config import AppConfig


def build_demo(config: AppConfig | None = None) -> gr.Blocks:
    config = config or AppConfig()
    agent = SQLAgent(config)

    example_questions = [
        [None, "Which product category generated the highest revenue?"],
        [None, "Show total revenue by city."],
        [None, "How many paid-plan customers placed at least one completed order?"],
    ]

    with gr.Blocks(title="Self-Correcting SQL/Data Analyst") as demo:
        gr.Markdown("# Self-Correcting SQL/Data Analyst")
        gr.Markdown(
            "Upload a SQLite / CSV / Excel file and ask a business question. "
            "The app inspects schema, drafts SQL, executes it, and retries on failures."
        )
        gr.Markdown(
            "> **Note:** This demo may feel slow because it runs on free CPU-only cloud hardware and may make multiple model calls per question."
        )

        with gr.Row():
            file_input = gr.File(label="Upload .db / .sqlite / .csv / .xlsx", type="filepath")
            question_input = gr.Textbox(label="Ask a question", placeholder="Show total sales by region.")

        run_btn = gr.Button("Run analysis")

        with gr.Row():
            sql_output = gr.Code(label="Final SQL", language="sql")
            summary_output = gr.Textbox(label="Summary", lines=6)

        result_output = gr.Dataframe(label="Query result", wrap=True)
        schema_output = gr.Textbox(label="Schema context", lines=16)
        trace_output = gr.Code(label="Agent trace", language="json")

        run_btn.click(
            fn=agent.ask,
            inputs=[question_input, file_input],
            outputs=[schema_output, sql_output, result_output, summary_output, trace_output],
        )

        gr.Examples(examples=example_questions, inputs=[file_input, question_input])

    return demo
