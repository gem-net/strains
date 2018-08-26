from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Email


class StrainForm(FlaskForm):
    lab = StringField('lab', [Length(min=0, max=64)])
    entry = StringField('entry', [Length(min=0, max=12)])
    organism = StringField('organism', [Length(min=0, max=64)])
    strain = StringField('strain', [Length(min=0, max=64)])
    plasmid = StringField('plasmid', [Length(min=0, max=64)])
    marker1 = StringField('marker1', [Length(min=0, max=64)])
    marker2 = StringField('marker2', [Length(min=0, max=64)])
    origin = StringField('origin', [Length(min=0, max=64)])
    origin2 = StringField('origin2', [Length(min=0, max=64)])
    promoter = StringField('promoter', [Length(min=0, max=64)])
    benchling_url = StringField('benchling_url', [Length(min=0, max=64)])
    desc = StringField('desc', [Length(min=0, max=255)])
    submitter = StringField('submitter', [Length(min=0, max=64)])


class RequestForm(FlaskForm):
    email = StringField('Your preferred email address',
                        [DataRequired(), Email()])
    address = TextAreaField('Delivery address',
                            validators=[Length(min=0, max=144)])
    submit = SubmitField('Submit')
