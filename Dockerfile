# https://hub.docker.com/r/lukaszgryglicki/facade/
# Use debian-jessie as source
FROM debian
MAINTAINER Łukasz Gryglicki<lukaszgryglicki@o2.pl>
WORKDIR /facade
ADD . /facade
# Avoid mysql-server installer ask for password
RUN ./utilities/mysql_root_pwd.sh
# RUN wget https://repo.mysql.com/mysql-apt-config_0.8.6-1_all.deb
# Initial update apt-get
RUN apt-get update
# Install all essentials, also mysql-server 5.5 (will skip ask fopr password)
RUN apt-get install -y `cat requirements.txt`
# Initialize facade DB
RUN service mysql start && mysql -uroot -proot < utilities/mysql_init.sql
# Now upgrade mysql from 5.5.55 to 8.0 (will not ask for password, but without 5.5.55 istalled it would)
RUN apt-key adv --keyserver pgp.mit.edu --recv-keys 5072E1F5
# RUN echo 'deb http://repo.mysql.com/apt/debian jessie mysql-8.0' > /etc/apt/sources.list.d/mysql.list
RUN echo 'deb http://repo.mysql.com/apt/debian jessie mysql-5.7' > /etc/apt/sources.list.d/mysql.list
RUN apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server mysql-client
# RUN apt-get install -y mysql-server mysql-client
# Configure Apache's mod rewrite
RUN ln -s /etc/apache2/mods-available/rewrite.load /etc/apache2/mods-enabled/rewrite.load
RUN sed -i 's/AllowOverride None/AllowOverride All/' /etc/apache2/apache2.conf
# Add facade user and add him to sudoers to allow `sudo` usage
RUN useradd -p facade facade
RUN echo 'facade:facade' | chpasswd
RUN adduser facade sudo
# Set root password
RUN echo 'root:root' | chpasswd
# Set Apached document root with Facade tools
RUN rm -rf /var/www/html
RUN cp -R /facade/ /var/www/html
# This was to test Apache-PHP integration
# RUN cp php/info.php /var/www/html/info.php
# Start Apache & SSHD services and expose their ports (outside world will see 80->8888, 22->2222)
RUN service apache2 start
RUN service ssh start
EXPOSE 80 22
# Default server command
CMD /facade/server.sh
