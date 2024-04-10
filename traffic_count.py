import math
import cv2
import subprocess
import os
import numpy as np
from time import sleep


class TrafficCount:
    def __init__(
        self,
        file_path,
        count_line_percent,  # 计数线的位置，两个点xy坐标
        largura_min=80,  # 矩形的最小宽度
        altura_min=80,  # 矩形的最小高度
        offset=6,  # 允许的像素误差
    ):
        self.file_path = file_path
        self.largura_min = largura_min
        self.altura_min = altura_min
        self.offset = offset

        cap = cv2.VideoCapture(self.file_path)  # 打开视频文件
        self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        # 获取视频高度
        self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        print(count_line_percent)
        self.count_line = [
            int(count_line_percent[0] * self.width / 100),
            int(count_line_percent[1] * self.height / 100),
            int(count_line_percent[2] * self.width / 100),
            int(count_line_percent[3] * self.height / 100),
        ]
        print(self.count_line)

    def ffmpeg_video_writer(self, frames):
        output_path = os.path.splitext(self.file_path)[0] + "_processed.mp4"
        dimension = "{}x{}".format(self.width, self.height)

        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            dimension,
            "-pix_fmt",
            "bgr24",
            "-r",
            str(self.fps),
            "-i",
            "-",
            "-an",
            # "-vcodec",
            # "mpeg4",
            output_path,
        ]

        ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

        for frame in frames:
            ffmpeg_process.stdin.write(frame.tostring())

        ffmpeg_process.stdin.close()
        ffmpeg_process.wait()

        return output_path

    def _rectangle_center(self, x, y, w, h):
        return x + int(w / 2), y + int(h / 2)

    def _line_magnitude(self, x1, y1, x2, y2):
        lineMagnitude = math.sqrt(math.pow((x2 - x1), 2) + math.pow((y2 - y1), 2))
        return lineMagnitude

    def _point_to_line_distance(self, point, line):
        px, py = point
        x1, y1, x2, y2 = line
        line_magnitude = self._line_magnitude(x1, y1, x2, y2)
        if line_magnitude < 0.00000001:
            return float("inf")
        else:
            u1 = ((px - x1) * (x2 - x1)) + ((py - y1) * (y2 - y1))
            u = u1 / (line_magnitude * line_magnitude)
            if (u < 0.00001) or (u > 1):
                # 点到直线的投影不在线段内, 计算点到两个端点距离的最小值即为"点到线段最小距离"
                ix = self._line_magnitude(px, py, x1, y1)
                iy = self._line_magnitude(px, py, x2, y2)
                if ix > iy:
                    distance = iy
                else:
                    distance = ix
            else:
                # 投影点在线段内部, 计算方式同点到直线距离, u 为投影点距离x1在x1x2上的比例, 以此计算出投影点的坐标
                ix = x1 + u * (x2 - x1)
                iy = y1 + u * (y2 - y1)
                distance = self._line_magnitude(px, py, ix, iy)
            return distance

    def _is_within_count_line(self, point):
        distance = self._point_to_line_distance(point, self.count_line)
        return (distance <= self.offset) and (distance >= 0)

    def process_frame(self, car_count, detected, subtractor, frame):
        grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # 将帧转换为灰度图像
        blur = cv2.GaussianBlur(grey, (3, 3), 5)  # 对灰度图像进行高斯模糊
        mask = subtractor.apply(blur)  # 应用背景减法器，提取前景
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        erode = cv2.erode(mask, kernel)
        dilate = cv2.dilate(erode, kernel, iterations=3)
        dilatada = cv2.morphologyEx(dilate, cv2.MORPH_CLOSE, kernel)
        dilatada = cv2.morphologyEx(dilatada, cv2.MORPH_CLOSE, kernel)
        contorno, h = cv2.findContours(dilatada, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        cv2.line(
            img=frame,
            pt1=(self.count_line[0], self.count_line[1]),
            pt2=(self.count_line[2], self.count_line[3]),
            color=(255, 127, 0),
            thickness=3,
        )  # 绘制计数线

        # 绘制检测到的边框
        for _, c in enumerate(contorno):
            (x, y, w, h) = cv2.boundingRect(c)  # 获取轮廓的边界框坐标
            validar_contorno = (
                (w >= self.largura_min)
                and (h >= self.altura_min)
                and (w <= 5 * self.largura_min)
                and (h <= 5 * self.altura_min)
            )
            if not validar_contorno:  # 检查矩形的尺寸是否满足最小要求
                continue

            # 绘制边界框和中心点
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            center = self._rectangle_center(x, y, w, h)
            cv2.circle(frame, center, 4, (0, 0, 255), -1)
            detected.append(center)

            # 处理车辆通过计数线（在计数线边缘）
            for x, y in detected:
                if self._is_within_count_line([x, y]):
                    cv2.line(
                        img=frame,
                        pt1=(self.count_line[0], self.count_line[1]),
                        pt2=(self.count_line[2], self.count_line[3]),
                        color=(0, 127, 255),
                        thickness=3,
                    )
                    detected.remove((x, y))
                    car_count += 1

            # 绘制计数文字
            cv2.putText(
                img=frame,
                text="VEHICLE COUNT : " + str(car_count),
                org=(450, 70),
                fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                fontScale=2,
                color=(0, 0, 255),
                thickness=5,
            )
        return car_count

    def process_video(self):
        detected = []  # 检测到的车辆中心点列表
        car_count = 0  # 车辆计数
        frames = []

        cap = cv2.VideoCapture(self.file_path)  # 打开视频文件
        subtractor = cv2.createBackgroundSubtractorMOG2()
        self.fps = cap.get(cv2.CAP_PROP_FPS)

        while True:
            ret, frame = cap.read()  # 读取视频的一帧
            if not ret:
                break  # 视频帧读取完毕，跳出循环
            car_count = self.process_frame(car_count, detected, subtractor, frame)
            frames.append(frame)
        cap.release()
        return car_count, self.ffmpeg_video_writer(frames)

    def preview_frame(self):
        cap = cv2.VideoCapture(self.file_path)  # 打开视频文件
        _, frame = cap.read()  # 读取视频的一帧
        cv2.line(
            img=frame,
            pt1=(self.count_line[0], self.count_line[1]),
            pt2=(self.count_line[2], self.count_line[3]),
            color=(255, 127, 0),
            thickness=3,
        )  # 绘制计数线
        cap.release()
        return frame
