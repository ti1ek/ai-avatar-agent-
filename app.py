"""
AI Avatar Agent — Gradio UI
Multimodal restaurant guide for Almaty.

Run:
    python app.py
"""
import subprocess
import sys
from pathlib import Path

import gradio as gr

sys.path.insert(0, str(Path(__file__).parent))

# Ensure Playwright Chromium is installed (required by MCP servers)
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        p.chromium.executable_path  # raises if not installed
except Exception:
    print("[Setup] Chromium not found — installing via playwright...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)

from agent.pipeline import run_pipeline, transcribe_audio


async def _transcribe_to_text(audio_path: str | None, current_text: str) -> str:
    """Transcribe audio and merge with existing text input."""
    if not audio_path:
        return current_text or ""
    try:
        transcript = await transcribe_audio(audio_path)
        if not transcript:
            return current_text or ""
        if current_text and current_text.strip():
            return current_text.strip() + " " + transcript
        return transcript
    except Exception as e:
        print(f"[ASR] Transcribe error: {e}")
        return current_text or ""


async def _process(
    text_input: str,
    audio_input: str | None,
    image_input: str | None,
    generate_video: bool,
    history: list[dict],
):
    print(f"[_process] text={text_input!r} audio={audio_input} image={image_input} video={generate_video}", flush=True)
    try:
        result = await run_pipeline(
            text_input=text_input or None,
            audio_path=audio_input,
            image_path=image_input,
            conversation_history=history,
            generate_audio=generate_video,
            generate_video=generate_video,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        avatar_update = gr.update(visible=True)
        video_update = gr.update(value=None, visible=False)
        err_msg = [{"role": "assistant", "content": f"Ошибка: {e}"}]
        return err_msg, video_update, avatar_update, history

    user_text = result["user_text"] or text_input or "(изображение)"
    assistant_text = result["assistant_text"]
    video_url = result["video_url"]

    updated_history = list(history)
    if user_text:
        updated_history.append({"role": "user", "content": user_text})
    if assistant_text:
        updated_history.append({"role": "assistant", "content": assistant_text})

    chat_display = [
        {"role": m["role"], "content": m["content"]}
        for m in updated_history
    ]

    # Show video or fallback to static photo
    if video_url:
        avatar_update = gr.update(visible=False)
        video_update = gr.update(value=video_url, visible=True)
    else:
        avatar_update = gr.update(visible=True)
        video_update = gr.update(value=None, visible=False)

    return chat_display, video_update, avatar_update, updated_history


CSS = """
.gradio-container { max-width: 100% !important; padding: 0 32px !important; }
.contain { max-width: 100% !important; }

#avatar_placeholder label, #avatar_placeholder .label-wrap { display: none !important; }
#video_output label, #video_output .label-wrap { display: none !important; }

/* Hide toolbar buttons (download, share, fullscreen) on image and video */
#avatar_placeholder .icon-button-wrapper,
#avatar_placeholder button[aria-label],
#video_output .icon-button-wrapper,
#video_output button[aria-label] { display: none !important; }

#avatar_placeholder, #avatar_placeholder > div { padding: 0 !important; background: transparent !important; }
#avatar_placeholder img { width: 100% !important; height: 480px !important; object-fit: cover !important; display: block !important; }
#video_output, #video_output > div { padding: 0 !important; background: #000 !important; box-shadow: none !important; border: none !important; }
#video_output video { width: 100% !important; height: 480px !important; object-fit: contain !important; display: block !important; }

[data-testid="drop-text"] { display: none !important; }
.drop-text { display: none !important; }

/* Make audio input taller */
#voice_input { min-height: 80px !important; }
#voice_input > div { min-height: 80px !important; display: flex !important; flex-direction: column !important; justify-content: center !important; }

#voice_input select { display: none !important; }

/* Hide default Gradio loaders */
.eta-bar { display: none !important; }
.progress-bar { display: none !important; }
.progress-level { display: none !important; }
.progress-level-inner { display: none !important; }
.meta-text { display: none !important; }
.meta-text-center { display: none !important; }
.loader { display: none !important; }
.wrap.default.full.unpad_bottom.hide { display: none !important; }

/* Custom loading indicator */
.generating::after {
    content: "Думаю...";
    display: block;
    text-align: center;
    color: #f97316;
    font-size: 14px;
    font-weight: 500;
    padding: 8px;
    animation: pulse-text 1.2s ease-in-out infinite !important;
    animation-duration: 1.2s !important;
}
@keyframes pulse-text {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* Remove image upload animation/overlay */
.image-container .overlay { display: none !important; }
.upload-container .overlay { display: none !important; }
.image-frame .overlay { display: none !important; }
.pending { animation: none !important; opacity: 1 !important; }
.uploading { animation: none !important; }

/* Disable upload/pending animations */
.pending { animation: none !important; opacity: 1 !important; }
.uploading { animation: none !important; }
button { transition: background-color 0.1s !important; }
"""

CLEANUP_JS = """
() => {
    const clean = () => {
        const el = document.getElementById('voice_input');
        if (!el) return;
        el.querySelectorAll('select').forEach(s => s.style.display = 'none');
    };
    clean();
    setTimeout(clean, 500);
    setTimeout(clean, 1500);
    const obs = new MutationObserver(clean);
    obs.observe(document.body, { childList: true, subtree: true });
}
"""

with gr.Blocks(title="Ресторанный гид Алматы") as demo:

    gr.Markdown(
        """
        # Ресторанный гид Алматы
        Задай вопрос голосом или текстом. Можешь прислать фото ресторана для оценки.
        Агент ищет данные через **Chocolife** и **ABR Group**, оценивает фото ресторана, отвечает текстом или через видео-ответ.
        """
    )

    history_state = gr.State([])

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(label="Диалог", height=480)

        with gr.Column(scale=2):
            avatar_placeholder = gr.Image(
                value="avatar/my_photo.jpg",
                show_label=False,
                height=480,
                interactive=False,
                elem_id="avatar_placeholder",
            )
            video_output = gr.Video(
                show_label=False,
                height=480,
                visible=False,
                elem_id="video_output",
            )

    with gr.Row():
        with gr.Column(scale=3, elem_id="left_col"):
            text_input = gr.Textbox(
                placeholder="Где поужинать в центре Алматы на двоих, бюджет 10 000 тг?",
                label="Текстовый вопрос",
                lines=2,
            )
            image_input = gr.Image(
                label="Фото ресторана для оценки",
                type="filepath",
                height=180,
                sources=["upload"],
            )
        with gr.Column(scale=2, elem_id="right_col"):
            audio_input = gr.Audio(
                label="Голосовой вопрос",
                type="filepath",
                sources=["microphone"],
                elem_id="voice_input",
            )
            generate_video_cb = gr.Checkbox(label="Видео-ответ", value=False)
            submit_btn = gr.Button("Отправить ▶", variant="primary", size="lg")
            clear_btn = gr.Button("Очистить", variant="secondary")

    gr.Examples(
        examples=[
            ["Где поужинать в центре Алматы на двоих, бюджет 15 000 тг?", None, None],
            ["Найди скидки на рестораны в Алматы", None, None],
            ["Что есть в Del Papa и сколько стоит?", None, None],
            ["Посоветуй кофейню с хорошим Wi-Fi", None, None],
        ],
        inputs=[text_input, audio_input, image_input],
        label="Примеры запросов",
    )

    audio_input.change(
        fn=_transcribe_to_text,
        inputs=[audio_input, text_input],
        outputs=[text_input],
    )

    submit_btn.click(
        fn=_process,
        inputs=[text_input, audio_input, image_input, generate_video_cb, history_state],
        outputs=[chatbot, video_output, avatar_placeholder, history_state],
    )

    text_input.submit(
        fn=_process,
        inputs=[text_input, audio_input, image_input, generate_video_cb, history_state],
        outputs=[chatbot, video_output, avatar_placeholder, history_state],
    )

    def clear_all():
        return [], gr.update(value=None, visible=False), gr.update(visible=True), [], None, None, None

    clear_btn.click(
        fn=clear_all,
        outputs=[chatbot, video_output, avatar_placeholder, history_state, text_input, audio_input, image_input],
    )

    demo.load(js=CLEANUP_JS)


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        theme=gr.themes.Soft(primary_hue="orange"),
        css=CSS,
    )
