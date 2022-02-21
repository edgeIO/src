import os
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime


MONGO_URL = os.environ.get('CLUSTER_MONGO_URL')
MONGO_PORT = os.environ.get('CLUSTER_MONGO_PORT')
MONGO_ADDR_NODES = 'mongodb://' + str(MONGO_URL) + ':' + str(MONGO_PORT) + '/nodes'
MONGO_ADDR_JOBS = 'mongodb://' + str(MONGO_URL) + ':' + str(MONGO_PORT) + '/jobs'


NODES_FRESHNESS_INTERVAL = 60

mongo_nodes = None
mongo_jobs = None

app = None


def mongo_init(flask_app):
    global mongo_nodes, mongo_jobs
    global app

    app = flask_app

    app.config["MONGO_URI"] = MONGO_ADDR_NODES
    mongo_nodes = PyMongo(app, uri=MONGO_ADDR_NODES)
    mongo_jobs = PyMongo(app, uri=MONGO_ADDR_JOBS)
    app.logger.info("init mongo")


def mongo_insert(obj):
    global mongo_nodes
    app.logger.info("inserting...")
    nodes = mongo_nodes.db.nodes
    node_id = nodes.insert_one(obj).inserted_id
    app.logger.info(node_id)
    return node_id


def mongo_findbyid(id):
    global mongo_nodes
    return mongo_nodes.db.nodes.find_one(id).inserted_id


def mongo_find_one_node():
    """Finds first cluster occurrence"""
    global mongo_nodes
    return mongo_nodes.db.nodes.find_one()


def mongo_find_node_by_name(name):
    """Finds first cluster occurrence"""
    global mongo_nodes
    try:
        return mongo_nodes.db.nodes.find_one({'node_info.host': name})
    except Exception as e:
        return "Error"


def mongo_find_all_nodes():
    global mongo_nodes
    return mongo_nodes.db.nodes.find()


def mongo_find_all_active_nodes():
    global mongo_nodes
    app.logger.info('Finding the active worker nodes...')
    now_timestamp = datetime.now().timestamp()
    return mongo_nodes.db.nodes.find(
        {'last_modified_timestamp': {'$gt': now_timestamp - NODES_FRESHNESS_INTERVAL}})


def mongo_set_job_as_scheduled(job_id, node_id):
    global mongo_nodes
    app.logger.info('Setting Job {0} as SCHEDULED for Node {1}'.format(job_id, node_id))

    # set job as Scheduled and set its associated node
    mongo_jobs.db.jobs.update_one({'_id': ObjectId(job_id)},
                                  {'$set': {'status': 'NODE_SCHEDULED', 'scheduled_node': node_id, 'replicas': 1}})

    # for the node, add a job
    mongo_nodes.db.nodes.update_one({'_id': ObjectId(node_id)}, {'$push': {'jobs': job_id}})
    return 1


def mongo_find_node_by_id_and_update(id, key, value):
    global mongo_nodes

    app.logger.info('update..')
    # node = mongo_workers.db.nodes.find_one({'_id': id})
    # app.logger.info(node)

    mongo_nodes.db.nodes.find_one_and_update({'_id': ObjectId(id)},
                                             {'$set': {key: value}},
                                             upsert=True)
    return 1

def mongo_find_node_by_id(id):
    global mongo_nodes
    app.logger.info(f"Get node {id}")
    return mongo_nodes.db.nodes.find_one({"_id": ObjectId(id)})

def mongo_find_job_by_microservice_id(application_id, microservice_id):
    global mongo_jobs
    app.logger.info(f"Get job with applicationID={application_id} and microserviceID={microservice_id}")
    return mongo_jobs.db.jobs.find_one({"applicationID": application_id, "microserviceID": microservice_id})

def mongo_get_vivaldi_data():
    global mongo_nodes
    app.logger.info(f"Query Vivaldi data from all workers")
    return mongo_nodes.db.nodes.find({}, {"vivaldi_vector": 1, "vivaldi_height": 1, "vivaldi_error": 1})

def mongo_get_geolocation_data():
    global mongo_nodes
    app.logger.info(f"Query geographic location data from all workers")
    return mongo_nodes.db.nodes.find({}, {"lat": 1, "long": 1})