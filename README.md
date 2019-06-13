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

The code in this repository assumes a Python 3 environment.

You can replicate the environment used to run the C-GEM Strains app by using conda
to install the virtual environment specified by the supplied environment file, 
`environment.lock.yaml`. This file specifies all dependendices, including 
precise version numbers.

With a Conda distribution installed, you can create a virtual environment as
follows:

```bash
conda env create -n strains -f environment.lock.yaml
```


### env file

A single environment file (.env) is used to specify all variables specific to 
your server. A demo file (`.env.demo`) has been provided, which you should 
update and rename to `.env`. 

This file is used to specify:
- the location of your python virtual environment (full path to directory that
includes the bin/ and lib/ subdirectories).
- the URL where the app will be served
- the server address (e.g. localhost or 127.0.0.1)
- port numbers for running the Bokeh server and Flask app
- a location for saving a local copy of downloaded strains data
- the path to a GSuite credentials file, in JSON format. The corresponding user 
must have read permission on the corresponding Strains sheet in Team Drive
- google service account credential information
- a local URL for the bokeh server
- development and production database details
- mail server configuration for user alerts


### Database setup

Database tables (used for tracking shipment requests and discussion) 
are defined in `oauth/models.py` and will be created automatically by 
SQLAlchemy, triggered by the line `db.create_all()` at the end of the module. 
Before running the apps for the first time, first make sure that you have 
created the database using the credentials you provided in the env file.


### Running the apps

The Bokeh server app should be started first, and can be initiated by running 
the `start_strains_bokeh.sh` script. This sets up the environment and runs 
the appropriate `bokeh serve` command to start the Bokeh server.

The Flask app can be initiated by running the `start_strains.sh` script, which
contains the appropriate `flask run` command.

Once both components are running, the combined app will be accessible in your 
browser at the URL you specified in the env file.
