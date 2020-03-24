FROM ubuntu:19.04

MAINTAINER Nick Hainke <vincent@systemli.org>, Christian Sieber<c.sieber@tum.de>, Susanna Schwarzmann<susanna.schwarzmann@inet.tu-berlin.de>

# Install dependencies
RUN apt update && \
    apt remove -y python && \
    apt install -y unzip python3 python3-pip bc autoconf automake build-essential libass-dev libfreetype6-dev \
                   git libsdl2-dev libtheora-dev libtool libva-dev libvdpau-dev libvorbis-dev libxcb1-dev libxcb-shm0-dev \
                   libxcb-xfixes0-dev pkg-config texinfo wget zlib1g-dev libx265-dev && \
    pip3 install --upgrade pandas && \ 
    pip3 install ffmpeg_quality_metrics && \
    apt-get clean autoclean && \
    apt-get autoremove && \
    rm -rf /var/lib/{apt,dpkg,cache,log}

# Install ffmpeg
WORKDIR /tools

# version with libvmaf
RUN apt install -y xz-utils && \
	wget https://johnvansickle.com/ffmpeg/builds/ffmpeg-git-amd64-static.tar.xz -O ffmpeg.tar.xz && \
	tar xf ffmpeg.tar.xz && \
	mv ffmpeg-* ffmpeg

ENV PATH="/tools/ffmpeg:${PATH}"
RUN cp -r /tools/ffmpeg/model /usr/local/share/model


# Add the (relevant) git content
COPY scripts/ /tools/scripts
COPY video_encode.py /tools/

# Fix permissions
RUN chmod o+r+w /tools && \
    chmod +x ./video_encode.py

VOLUME ["/videos", "/results", "/tmpdir"]

ENTRYPOINT ["./video_encode.py"]

