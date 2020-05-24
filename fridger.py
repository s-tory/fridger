# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from collections import deque
from subprocess import call
from dataclasses import dataclass
from typing import ClassVar, List, Dict, Tuple, NamedTuple
import json
import pathlib
import signal
from tempfile import NamedTemporaryFile

import picamera
import picamera.array
import cv2
import numpy as np
from matplotlib import pyplot as plt
import requests

import constants as cnst
import settings as stg


class TimeStampedImage(NamedTuple):
    image: np.ndarray
    time_stamp: datetime


@dataclass
class Fridger(object):
    is_running: bool = False
    is_door_open: bool = False

    def __post_init__(self):
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        self._camera = picamera.PiCamera()
        self._camera.resolution = cnst.CAMERA_RESOLUTION
        self._ring_buffer_of_time_stamped_images = deque(
            maxlen=cnst.RING_BUFFER_OF_TIME_STAMPED_IMAGES_MAXLEN)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._camera .close()

    def run(self):
        self.is_running = True

        door_closed_datetime = None

        while self.is_running:
            captured_image = self._capture_image()
            captured_datetime = datetime.now()
            print('captured image.')

            if stg.IS_PREVIEW_ENABLED:
                self._preview_image(captured_image)

            if stg.IS_DRAW_HISTGRAM_ENABLED:
                self._draw_histgram(captured_image)

            has_door_open = self.is_door_open
            average_brightness = np.average(captured_image)
            print('average brightness = {}'.format(average_brightness))
            self.is_door_open = average_brightness > cnst.AVERAGE_BRIGHTNESS_THRESHOLD_FOR_DOOR_OPEN

            if self.is_door_open and not has_door_open:
                print('detected door open.')

            if self.is_door_open:
                time_stamped_image = TimeStampedImage(
                    captured_image, captured_datetime)
                self._ring_buffer_of_time_stamped_images.append(
                    time_stamped_image)

            if not self.is_door_open and has_door_open:
                print('detected door close.')
                door_closed_datetime = captured_datetime

            if door_closed_datetime is not None:
                passed_seconds = (captured_datetime -
                                  door_closed_datetime).total_seconds()

                if passed_seconds > stg.DELAY_SECONDS_SINCE_DOOR_CLOSED:
                    door_closed_datetime = None

                    try:
                        picked = self._pick_up_time_stamped_image()

                        if stg.IS_SAVE_IMAGE_TO_LOCAL_ENABLED:
                            self._save_time_stamped_image(picked)

                        if stg.IS_POST_IMAGE_TO_SLACK_ENABLED:
                            self._post_time_stamped_image(picked)
                    except Exception:
                        print('continue.')
                    finally:
                        self._clear_ring_buffer_of_time_stamped_images()

    def stop(self, num, frame):
        print('detected SIGINT or SIGTERM.')

        self.is_running = False

    def _capture_image(self):
        with picamera.array.PiRGBArray(self._camera, size=stg.RESIZED_IMAGE_RESOLUTION) as stream:
            self._camera.capture(
                stream, format='bgr', resize=stg.RESIZED_IMAGE_RESOLUTION)

            image = cv2.rotate(
                stream.array, cv2.ROTATE_90_COUNTERCLOCKWISE)

            return image

    def _preview_image(self, image):
        cv2.imshow('preview', image)
        cv2.waitKey(1)

    def _draw_histgram(self, image):
        color = ('b', 'g', 'r')
        for i, col in enumerate(color):
            histr = cv2.calcHist(
                [image], [i], None, [256], [0, 256])
            plt.plot(histr, color=col)
            plt.xlim([0, 256])
        plt.pause(0.01)  # plt.show()だと閉じる待ちになる

    def _pick_up_time_stamped_image(self, nth_from_latest=cnst.PICK_UP_NTH_IMAGE_FROM_LATEST):
        if nth_from_latest < 1 or cnst.RING_BUFFER_OF_TIME_STAMPED_IMAGES_MAXLEN - 1 < nth_from_latest:
            msg = 'invalid argument: nth_from_latest = {}'.format(
                nth_from_latest)
            print(msg)
            raise Exception(msg)

        if len(self._ring_buffer_of_time_stamped_images) < nth_from_latest:
            msg = 'buffer of time stamped images is NOT enough.'
            print(msg)
            raise Exception(msg)

        for _ in range(0, nth_from_latest-1):
            self._ring_buffer_of_time_stamped_images.pop()

        return self._ring_buffer_of_time_stamped_images.pop()

    def _clear_ring_buffer_of_time_stamped_images(self):
        self._ring_buffer_of_time_stamped_images.clear()
        print('cleared ring buffer of time stamped images.')

    def _save_time_stamped_image(self, time_stamped_image):
        save_directory_path = pathlib.Path(stg.IMAGES_DIRECTORY_PATH)
        if not save_directory_path.exists():
            save_directory_path.mkdir()
            print('created "{}" diectory.'.format(save_directory_path))

        time_stamp = time_stamped_image.time_stamp
        save_file_name = 'fridger_{}.jpg'.format(
            time_stamp.strftime('%Y-%m-%d-%H-%M-%S_%f'))
        save_file_path = save_directory_path.joinpath(save_file_name)

        image = time_stamped_image.image

        cv2.imwrite(str(save_file_path), image)
        print('saved "{}".'.format(save_file_path))

    def _post_time_stamped_image(self, time_stamped_image):
        time_stamp = time_stamped_image.time_stamp
        post_file_name = 'fridger_{}.jpg'.format(
            time_stamp.strftime('%Y-%m-%d-%H-%M-%S_%f'))

        image = time_stamped_image.image
        result, jpg_binary = cv2.imencode(".jpg", image)

        param = {
            'token': stg.SLACK_OAUTH_ACCESS_TOKEN,
            'channels': stg.SLACK_CHANNEL_ID,
            'initial_comment': stg.SLACK_COMMENT_WHEN_UPLOAD,
            'title': post_file_name
        }
        files = {'file': jpg_binary}
        response = requests.post(url=cnst.SLACK_FILES_UPLOAD_URL,
                                 params=param, files=files)
        loaded = json.loads(response.text)
        
        if loaded['ok'] is True:
            print('posted "{}".'.format(post_file_name))
        else:
            msg = 'could NOT post "{}".'.format(post_file_name)
            print(msg)
            print(json.dumps(loaded, indent=2))

            raise Exception(msg)


if __name__ == '__main__':
    with Fridger() as fr:
        fr.run()
