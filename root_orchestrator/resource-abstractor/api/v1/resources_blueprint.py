from bson import ObjectId
from db.clusters_db import (
    create_cluster,
    find_cluster_by_id,
    find_clusters,
    update_cluster_information,
)
from db.clusters_helper import build_filter
from db.jobs_db import find_job_by_id
from flask.views import MethodView
from flask_smorest import Blueprint
from marshmallow import INCLUDE, Schema, fields
from werkzeug import exceptions

resourcesblp = Blueprint("Resources Info", "resources_info", url_prefix="/api/v1/resources")


class ResourceSchema(Schema):
    _id = fields.String()
    cluster_name = fields.String()
    cluster_location = fields.String()
    ip = fields.String()
    port = fields.String()
    active_nodes = fields.Integer()
    active = fields.Boolean()

    memory_in_mb = fields.Integer()
    total_cpu_cores = fields.Integer()
    total_gpu_cores = fields.Integer()
    aggregated_cpu_percent = fields.Float()
    available_memory = fields.Float()
    total_gpu_percent = fields.Integer()
    virtualization = fields.List(fields.String())
    last_modified_timestamp = fields.Float()


class ResourceFilterSchema(Schema):
    active = fields.Boolean()
    job_id = fields.String()
    cluster_name = fields.String()
    ip = fields.String()


@resourcesblp.route("/")
class AllResourcesController(MethodView):
    @resourcesblp.arguments(ResourceFilterSchema, location="query")
    @resourcesblp.response(200, ResourceSchema(many=True), content_type="application/json")
    def get(self, query={}):
        filter = query
        job_id = filter.get("job_id")
        if job_id:
            if ObjectId.is_valid(job_id) is False:
                raise exceptions.BadRequest()

            job = find_job_by_id(job_id)
            if job is None:
                raise exceptions.NotFound()

            cluster_id = job.get("cluster")
            if cluster_id is None:
                raise exceptions.NotFound()

            filter["cluster_id"] = cluster_id
        filter = build_filter(query)

        return list(find_clusters(filter))

    @resourcesblp.arguments(ResourceSchema(unknown=INCLUDE), location="json")
    @resourcesblp.response(200, ResourceSchema, content_type="application/json")
    def put(self, *args, **kwargs):
        data = None
        if args and len(args) > 0 and args[0] and type(args[0]) is dict:
            data = args[0]

        if data is None:
            raise exceptions.BadRequest()

        return create_cluster(data)


@resourcesblp.route("/<resourceId>")
class ResourceController(MethodView):
    @resourcesblp.response(200, ResourceSchema, content_type="application/json")
    def get(self, resourceId):
        if ObjectId.is_valid(resourceId) is False:
            raise exceptions.BadRequest()

        cluster = find_cluster_by_id(resourceId)
        if cluster is None:
            raise exceptions.NotFound()

        return cluster

    @resourcesblp.arguments(ResourceSchema(unknown=INCLUDE), location="json")
    @resourcesblp.response(200, ResourceSchema, content_type="application/json")
    def patch(self, *args, **kwargs):
        resource_id = kwargs["resourceId"]
        data = None
        if args and len(args) > 0 and args[0] and type(args[0]) is dict:
            data = args[0]

        if data is None:
            raise exceptions.BadRequest()

        if ObjectId.is_valid(resource_id) is False:
            raise exceptions.BadRequest()

        return update_cluster_information(resource_id, data)
