cs3240-project
==============



Usage
-----

####Client

To run a watchdog client:
```bash
python client/observer.py directoryname
```

This starts a polling python script that watches for changes in directoryname. It will attempt to reflect those changes in the api running on localhost.

To run the client user driver.py

####Server


If you want to use the api run:
```bash
python server/api.py
```

To use the webserver run:
```bash
python server/app.py
```

Note that the api will run on port 5000 and the webserver will be on 19919.
