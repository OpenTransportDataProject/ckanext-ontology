# ckanext-ontology

This is an extension which brings ontology functionality into CKAN.



## Installation

1. Activate your CKAN virtual environment, for example:

        $ . /usr/lib/ckan/default/bin/activate

2.  Install the extension on your virtualenv:

        (pyenv) $ pip install -e git+https://github.com/OpenTransportDataProject/ckanext-ontology.git#egg=ckanext-ontology

3.  Install the extension requirements:

        (pyenv) $ cd /usr/lib/ckan/default/src/
        (pyenv) $ pip install -r ckanext-ontology/requirements.txt

4.  Enable the ontology plugin in your ini file (development.ini or production.ini) by appending 'ontology' to the specified line:

        ckan.plugins = ... ontology

5.  Restart apache:

        sudo service apache2 restart

