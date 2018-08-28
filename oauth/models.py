from datetime import datetime

from flask_login import UserMixin

from oauth import db, lm


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(64), nullable=False, unique=True)
    display_name = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(64), nullable=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    in_cgem = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<User {}>'.format(self.email)


@lm.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class Strain(db.Model):
    __tablename__ = 'strains'
    lab = db.Column(db.String(64), primary_key=True)
    entry = db.Column(db.String(12), primary_key=True)
    organism = db.Column(db.String(64))
    strain = db.Column(db.String(64))
    plasmid = db.Column(db.String(64))
    marker1 = db.Column(db.String(64))
    marker2 = db.Column(db.String(64))
    origin = db.Column(db.String(64))
    origin2 = db.Column(db.String(64))
    promoter = db.Column(db.String(64))
    benchling_url = db.Column(db.String(64))
    desc = db.Column(db.String(255))
    submitter = db.Column(db.String(64))

    def __repr__(self):
        return '<Strain {}_{}:{}>'.format(self.lab, self.entry, self.plasmid)

    def get_strain_id(self):
        return '{}_{}'.format(self.lab, self.entry)


class Request(db.Model):
    __tablename__ = 'requests'
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    strain_lab = db.Column(db.String(64), nullable=False)
    strain_entry = db.Column(db.String(12), nullable=False)
    shipper_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    creation_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(64), default='unassigned')
    is_active = db.Column(db.Boolean, default=True)
    delivery_address = db.Column(db.String(255))
    preferred_email = db.Column(db.String(64), nullable=True)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['strain_lab', 'strain_entry'],
            ['strains.lab', 'strains.entry']),)

    strain = db.relationship('Strain', backref='requests',
                             foreign_keys=[strain_lab, strain_entry])
    requester = db.relationship('User', backref='requests_sent',
                                foreign_keys=[requester_id])
    shipper = db.relationship('User', backref='requests_handled',
                              foreign_keys=[shipper_id])

    def __repr__(self):
        return '<Request {}: {}_{}>'.format(self.requester.email,
                                            self.strain_lab,
                                            self.strain_entry)


db.create_all()
