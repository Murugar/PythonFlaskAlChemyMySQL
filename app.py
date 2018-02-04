#!flask/bin/python
from sqlalchemy.exc import DataError
from sqlalchemy.ext.declarative import declarative_base

from flask import Flask, jsonify, send_from_directory
from flask import request, abort, make_response
from flask_marshmallow import Marshmallow
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
ma = Marshmallow(app)
# ----------------------------------------------------------------------------------------------------------------------
#
# Flask_SQLAlchemy Setup to talk to MySQL.
# Note:  Yes, I hard coded my username and password for my local MySQL instance.
# Do I need to do the encoding to ISO-8859-1 to deal with weird characters in my raw DB tables?
#

app.config["SQLALCHEMY_DATABASE_URI"] = 'mysql+pymysql://root:good1234@localhost/tams'
app.config["SQLALCHEMY_ECHO"] = True
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

Base = declarative_base()


class Test(db.Model):
    __tablename__ = 'test'
    id = db.Column('id', db.Integer, primary_key=True)
    first = db.Column(db.String(45))
    last = db.Column(db.String(45))

    def __init__(self, first, last):
        self.first = first
        self.last = last


#
# Basic input validation.  Just get an appropriately-sized substring if its too long, or throw an error if it's None
#
def validate_test(intest):
    outtest = intest

    if intest is None:
        raise DataError

    if len(intest) > 45:
        outtest = intest[0:44]

    return outtest


class TestSchema(ma.Schema):
    class Meta:
        # Fields to expose
        fields = ('id', 'first', 'last', '_links')

    # Smart hyperlinking so now we're HATEOAS.
    _links = ma.Hyperlinks({
        'self': ma.URLFor('get_dd_id', dd_id='<id>'),
        'collection': ma.URLFor('get_dd')
    })


test_schema = TestSchema()
test_schemas = TestSchema(many=True)


# ----------------------------------------------------------------------------------------------------------------------
#
# Flask Routing functions.


#
# Return some JSON in the event of an error returned.
#
@app.errorhandler(404)
def not_found(error):
    if error:
        return make_response(jsonify({'error': "{}".format(error)}), 404)
    return make_response(jsonify({'error': 'Not found'}), 404)


#
# Return all of the DurkaDurkas in the system.
#
@app.route('/rest/v1.0/test', methods=['GET'])
def get_dd():
    dds = db.session.query(Test.id, Test.first, Test.last)
    return durkadurkas_schema.jsonify(dds)


#
# Return a specific Test given an id.
#
@app.route('/rest/v1.0/test/<int:dd_id>', methods=['GET'])
def get_dd_id(dd_id):
    dds = db.session.query(Test.id, Test.first, Test.last).filter(Test.id == dd_id)
    return test_schema.jsonify(dds)


#
# Create a new Test by posting it.
#
@app.route('/rest/v1.0/test', methods=['POST'])
def create_dd():
    if not request.json or 'first' not in request.json or 'first' not in request.json:
        abort(400)
    try:
        i2 = Test(first=validate_test(request.json['first']),
                        last=validate_test(request.json['first']))
        db.session.add(i2)
        db.session.commit()
        return test_schema.jsonify(i2)
    except DataError:
        abort(500)


#
# Update a DurkaDurka's fields with some new data given a DurkaDurka id.
#
@app.route('/rest/v1.0/test/<int:dd_id>', methods=['PUT'])
def update_dd(dd_id):
    if not request.json or 'first' not in request.json or 'first' not in request.json:
        abort(400)

    q = db.session.query(Test).filter(Test.id == dd_id)
    record = q.one()

    try:
        record.first = validate_test(request.json['first'])
        record.last = validate_test(request.json['last'])
        db.session.commit()
    except DataError:
        abort(500)

    return test_schema.jsonify(record)


#
# Route and Function to delete the Test given a Test id.
#
@app.route('/rest/v1.0/test/<int:dd_id>', methods=['DELETE'])
def delete_dd(dd_id):
    try:
        d = db.session.query(Test).filter(Test.id == dd_id).one_or_none()
    except:
        return jsonify({'result': False})

    if d is None:
        return jsonify({'result': False})
    else:
        try:
            db.session.delete(d)
            db.session.commit()
            return jsonify({'result': True})
        except:
            return jsonify({'result': False})


#
# Default route.  Not sure what typically goes here on an API.
# TODO: Figure out what goes in the default route for an API.
#
@app.route('/')
def index():
    return "Test Rest"


#
# Trying to return a YAML file so that I can pull this into swagger...
#
@app.route('/specs')
def specs():
    return send_from_directory('.', 'test.yaml')

# ----------------------------------------------------------------------------------------------------------------------
#
# Main function to kick off the Flask App.
# Notice the threaded=True--that's how to kick off multithreading (Thanks to to Paul M!)
# With the multithreading, the rollbacks don't block the database updates.
#

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
