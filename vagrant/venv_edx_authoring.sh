#!/bin/bash
export HOME=/home/vagrant
export WORKON_HOME=$HOME/.virtualenvs
source /usr/local/bin/virtualenvwrapper.sh
mkvirtualenv -a /home/vagrant/edx_lti_authoring -r /home/vagrant/edx_lti_authoring/edx_lti_authoring/requirements/local.txt edx_lti_authoring
