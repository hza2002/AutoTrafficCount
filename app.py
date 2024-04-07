import gradio as gr
from traffic_count import TrafficCount

with gr.Blocks(title="Auto Traffic Count") as demo:
    gr.Markdown(
        """
        # Auto Traffic Count
        """
    )
    with gr.Row():
        input_video = gr.Video(label="Input", show_download_button=True)
        preview_img = gr.Image(label="Preview")
        output_video = gr.Video(label="Output", show_download_button=True)
    with gr.Row():
        with gr.Column(scale=2):
            with gr.Row():
                startX = gr.Slider(0, 100, label="Start X%")
                startY = gr.Slider(0, 100, label="Start Y%")
            with gr.Row():
                endX = gr.Slider(0, 100, label="End X%")
                endY = gr.Slider(0, 100, label="End Y%")
        start = gr.Button(value="Start", scale=1)
        result = gr.Textbox(label="The number of detected cars", scale=1)
        with gr.Column(scale=2):
            example = gr.Examples(
                examples=[["example.mp4", 2, 82, 93, 82]],
                inputs=[input_video, startX, startY, endX, endY],
            )

        @start.click(
            inputs=[input_video, startX, startY, endX, endY],
            outputs=[result, output_video],
        )
        def proccess_video(video_path, startX, startY, endX, endY):
            count_line_percent = [startX, startY, endX, endY]
            print(count_line_percent)
            return TrafficCount(
                file_path=video_path, count_line_percent=count_line_percent
            ).process_video()

        def preview_frame(video_path, startX, startY, endX, endY):
            count_line_percent = [startX, startY, endX, endY]
            img = TrafficCount(
                file_path=video_path, count_line_percent=count_line_percent
            ).preview_frame()
            return img

        input_video.upload(
            fn=preview_frame,
            inputs=[input_video, startX, startY, endX, endY],
            outputs=preview_img,
        )
        startX.change(
            fn=preview_frame,
            inputs=[input_video, startX, startY, endX, endY],
            outputs=preview_img,
        )
        startY.change(
            fn=preview_frame,
            inputs=[input_video, startX, startY, endX, endY],
            outputs=preview_img,
        )
        endX.change(
            fn=preview_frame,
            inputs=[input_video, startX, startY, endX, endY],
            outputs=preview_img,
        )
        endY.change(
            fn=preview_frame,
            inputs=[input_video, startX, startY, endX, endY],
            outputs=preview_img,
        )


demo.launch(share=True)
