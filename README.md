# The C-GEM Strains app

![The Strains dashboard](strains_dashboard.png)

This app consists of two sub-apps which must run simultaneously:
- a Bokeh server app, with code in `bk_server`;
- a Flask app, with code in `oauth`.

The Bokeh server app is used to generate the interactive bar chart and table on 
the homepage. It interacts with the user-facing Flask app, which provides the 
rest of the application interface and responds to HTTP requests. 

## Setup instructions

### Python package dependencies

The code in this repository assumes a Python 3 environment. Python dependencies 
are specified in two `requirements.txt` files. Install with `pip` using:
```
pip install -r bk_server/requirements.txt
pip install -r oauth/requirements.txt
```

### env files

Both apps require an env file in their respective directories. These files 
specify configuration detail that is not suitable for hard-coding. Demo env files, 
`bk_server/.env_demo` and `oauth/.env_demo` have been provided, which you should 
update. In both cases, rename the file to `.env`. 

The `bk_server` env file is used to specify:
- a location for saving a local copy of downloaded strains data, 
- the path to a GSuite credentials file, in JSON format. The corresponding user 
must have read permission on the corresponding Strains sheet in Team Drive.

The `oauth` env file requires additional information:
- google service account credential information
- a local URL for the bokeh server
- development and production database details
- mail server configuration for user alerts


### Database setup

Database tables are defined in `oauth/models.py` and will be created 
automatically by SQLAlchemy, triggered by the line `db.create_all()` at the 
end of the module. Before running the apps for the first time, first make sure
that you have created the database using the credentials you provided in the 
`oauth` env file.


### Running the apps

The Bokeh server app should be started first, and can be initiated by running 
the command below in bash. Update `myserverip` to specify your server address; 
replace `strains.gem-net.net` with your final url; and update the path to your 
`bk_server` directory.

```bash
bokeh serve --port 5101 --show \
 --address myserverip \
 --allow-websocket-origin=myserverip:5101 \
 --allow-websocket-origin=strains.gem-net.net \
 /path/to/bk_server
```

The Flask app can then be served with the command below. This command sets two 
environment variables: the path to `app.py`, and server mode 
(`production` or `development`). The port must be the same as that provided for 
the Bokeh app.

```bash
FLASK_APP=/path/to/oauth/app.py FLASK_ENV=production /path/to/flask run --port 5100
``` 
