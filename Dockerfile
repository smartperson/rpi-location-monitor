# base-image for python on any machine using a template variable,
# see more about dockerfile templates here:http://docs.resin.io/pages/deployment/docker-templates
FROM resin/raspberry-pi-python

# use apt-get if you need to install dependencies,
# for instance if you need ALSA sound utils, just uncomment the lines below.
# RUN apt-get update && apt-get install -yq \
#    alsa-utils libasound2-dev && \
#    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -yq \
		python-smbus libfreetype6-dev python-imaging && \
		apt-get clean && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/joan2937/pigpio && cd pigpio && make && make install && cd .. && rm -rf pigpio

# Set our working directory
WORKDIR /usr/src/app

# Copy requirements.txt first for better cache on later pushes
COPY ./requirements.txt /requirements.txt

# pip install python deps from requirements.txt on the resin.io build server
RUN pip install -r /requirements.txt

# This will copy all files in our root to the working  directory in the container
COPY . ./

# switch on systemd init system in container
ENV INITSYSTEM on

# main.py will run when container starts up on the device
CMD modprobe -r i2c_bcm2708 && modprobe i2c_bcm2708 baudrate=50000 && modprobe i2c-dev && pigpiod && python src/main.py
