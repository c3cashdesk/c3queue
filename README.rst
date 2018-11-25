c3queue
-------

``c3queue`` is a small Python web app, generating the page at
https://c3queue.de. It displays the (historical and current) waiting time at
the ticket queue at Chaos Communication Congress.

``c3queue`` integrates with postix_. If you want to use it with your postix
installation, you'll have to empty the ``c3queue.csv`` file, and choose a
secret passphrase. Enter the passphrase in your postix configuration, and also
set it as environment variable ``C3SECRET`` when starting the c3queue server.

Other than that, install the requirements with ``pip install -r requirements.txt`` (you'll need Python 3.5+), and run your server with any of the methods in the aiohttp docs_, for example with gunicorn::

   gunicorn --bind unix:/run/gunicorn/c3queue --worker-class aiohttp.GunicornWebWorker c3queue:main


.. _postix: https://github.com/c3cashdesk/postix
.. _docs: https://aiohttp.readthedocs.io/en/stable/deployment.html
