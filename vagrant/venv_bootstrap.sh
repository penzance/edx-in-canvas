#!/bin/bash
# Set up virtualenv and migrate project
export HOME=/home/vagrant
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv -a /home/vagrant/edx_in_canvas -r /home/vagrant/edx_in_canvas/edx_in_canvas/requirements/local.txt edx_in_canvas 
workon edx_in_canvas
python manage.py migrate
