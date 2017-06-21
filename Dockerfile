# https://hub.docker.com/r/lukaszgryglicki/facade/
# Use debian-jessie as source
FROM debian
MAINTAINER Łukasz Gryglicki<lukaszgryglicki@o2.pl>
WORKDIR /facade
ADD . /facade
# Avoid mysql-server installer ask for password
RUN ./utilities/mysql_root_pwd.sh
# Initial update apt-get
RUN DEBIAN_FRONTEND=noninteractive apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y `cat requirements.txt`
# Initialize Facade DB
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
# Configure/Initialize Facade schema and admin/admin user
RUN service mysql restart && ./facade_setup.sh && echo "Setup complete"
RUN rm -rf /var/www/html
RUN cp -R /facade/ /var/www/html
EXPOSE 80
EXPOSE 22
# Default server command
CMD /facade/server.sh
