import os
import time
import argparse
from typing import List

import numpy as np
from PIL import Image as PILImage

# ROS
import rospy
from sensor_msgs.msg import Image

from topic_names import IMAGE_TOPIC


def pil_to_ros_image(pil_img: PILImage.Image, encoding: str = "rgb8") -> Image:
    img = np.asarray(pil_img)
    if img.ndim == 2:
        # gray to rgb
        img = np.repeat(img[..., None], 3, axis=2)
    h, w, c = img.shape
    assert c in (3, 4), "Only RGB/RGBA images are supported"
    if c == 4:
        # drop alpha
        img = img[:, :, :3]
        c = 3

    ros_image = Image()
    ros_image.height = h
    ros_image.width = w
    ros_image.encoding = encoding
    ros_image.is_bigendian = 0
    ros_image.step = w * c
    ros_image.data = img.tobytes()
    return ros_image


def list_images(directory: str) -> List[str]:
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    files = [f for f in os.listdir(directory) if os.path.splitext(f)[1].lower() in exts]
    # 숫자 파일명이면 숫자 기준 정렬, 아니면 사전식 정렬
    try:
        files = sorted(files, key=lambda x: int(os.path.splitext(x)[0]))
    except Exception:
        files = sorted(files)
    return [os.path.join(directory, f) for f in files]


def main():
    parser = argparse.ArgumentParser(
        description="Publish images from a directory to a ROS Image topic"
    )
    parser.add_argument("--dir", required=True, type=str, help="Directory containing images")
    parser.add_argument("--rate", type=float, default=9.0, help="Publish rate (Hz)")
    parser.add_argument("--topic", type=str, default=IMAGE_TOPIC, help="ROS image topic")
    parser.add_argument("--loop", action="store_true", help="Loop over images continuously")
    args = parser.parse_args()

    assert os.path.isdir(args.dir), f"Directory not found: {args.dir}"
    image_paths = list_images(args.dir)
    assert len(image_paths) > 0, f"No images found in {args.dir}"

    rospy.init_node("image_dir_player", anonymous=False)
    pub = rospy.Publisher(args.topic, Image, queue_size=1)
    rate = rospy.Rate(args.rate)

    rospy.loginfo(f"Publishing {len(image_paths)} images from {args.dir} to {args.topic} at {args.rate} Hz")

    idx = 0
    while not rospy.is_shutdown():
        img_path = image_paths[idx]
        pil_img = PILImage.open(img_path).convert("RGB")
        msg = pil_to_ros_image(pil_img, encoding="rgb8")
        pub.publish(msg)
        idx += 1
        if idx >= len(image_paths):
            if args.loop:
                idx = 0
            else:
                rospy.loginfo("Finished publishing all images. Shutting down.")
                break
        rate.sleep()


if __name__ == "__main__":
    main()


