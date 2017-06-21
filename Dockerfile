# https://hub.docker.com/r/lukaszgryglicki/facade/
# Use debian-jessie as source
FROM debian
MAINTAINER Łukasz Gryglicki<lukaszgryglicki@o2.pl>
# Echo add newer/unstable package source
RUN echo 'deb http://ftp.debian.org/debian jessie-backports main' > /etc/apt/sources.list.d/sources.list
WORKDIR /facade
ADD . /facade
# Avoid mysql-server installer ask for password
RUN ./utilities/mysql_root_pwd.sh
# Initial update apt-get
RUN apt-key adv --keyserver pgp.mit.edu --recv-keys 5072E1F5
RUN echo 'deb http://repo.mysql.com/apt/debian jessie mysql-5.7' > /etc/apt/sources.list.d/mysql.list
RUN apt-get update
# Install all stable requirements
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y `cat requirements_stable.txt`
# Install all backports requirements
RUN DEBIAN_FRONTEND=noninteractive apt-get -t jessie-backports install -y `cat requirements_backports.txt`
# Initialize facade DB
RUN service mysql start && mysql -uroot -proot < utilities/mysql_init.sql
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
# Configure/Initialize Facade schema and admin/admin user
RUN service mysql restart && ./facade_setup.sh && echo "Setup complete"
EXPOSE 80
EXPOSE 22
# Default server command
CMD /facade/server.sh
