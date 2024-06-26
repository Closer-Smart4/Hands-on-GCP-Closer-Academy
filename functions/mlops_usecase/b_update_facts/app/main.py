"""This module contains a cloud function that updates a facts BigQuery table.

With data from another table and publishes a message to a Pub/Sub topic.

The function loads the necessary GCP clients, environment variables, and SQL
query to update the BigQuery table.
It then executes the query and publishes a message to the Pub/Sub topic.
"""

import base64
import json
import os
from pathlib import Path

import functions_framework
from cloudevents.http import CloudEvent
from google.cloud import bigquery, pubsub

try:
	from funcs import common, gcp_apis, models
except ImportError:
	from b_update_facts.app.funcs import (
		common,
		gcp_apis,
		models,
	)


def load_clients(gcp_project_id: str) -> models.GCPClients:
	"""Load the GCP clients.

	Args:
	    gcp_project_id (str): The GCP project ID.

	Returns:
	    GCPClients: A tuple of GCP clients.
	        With the following attributes:
	            bigquery_client: A bigquery client.
	            publisher: A pubsub publisher client.
	"""
	bigquery_client = bigquery.Client(project=gcp_project_id)
	publisher = pubsub.PublisherClient()

	return models.GCPClients(bigquery_client=bigquery_client, publisher=publisher)


##############################
# 1. Environment variables ###
##############################


def _env_vars() -> models.EnvVars:
	"""Returns an instance of the EnvVars class with environment variables set.

	Returns:
	    models.EnvVars: An instance of the EnvVars class with environment variables set.
	"""
	# fqn = fully qualified name
	# A table fqn is in the format: project_id.dataset_id.table_id

	return models.EnvVars(
		gcp_project_id=os.getenv('_GCP_PROJECT_ID', 'gcp_project_id'),
		bq_staging_table_fqn=f"""{os.getenv("_GCP_PROJECT_ID", "gcp_project_id")}.\
{os.getenv("_BIGQUERY_DATASET_ID", "bq_table_staging_dst")}.\
{os.getenv("_BIGQUERY_STAGING_TABLE_ID", "bq_staging_table_fqn")}""",
		bq_facts_table_fqn=f"""{os.getenv("_GCP_PROJECT_ID", "gcp_project_id")}.\
{os.getenv("_BIGQUERY_DATASET_ID", "bq_table_fqn_dst")}.\
{os.getenv("_BIGQUERY_FACTS_TABLE_ID", "bq_facts_table_fqn")}""",
		topic_update_facts_complete=os.getenv('_TOPIC_UPDATE_FACTS_COMPLETE', 'topic_update_facts_complete'),
	)


if os.getenv('_CI_TESTING', 'no') == 'no':
	env_vars = _env_vars()
	gcp_clients = load_clients(gcp_project_id=env_vars.gcp_project_id)


@functions_framework.cloud_event
def main(cloud_event: CloudEvent) -> None:
	"""Entrypoint of the cloud function.

	Args:
	cloud_event (CloudEvent): The cloud event that triggered this function.
	"""
	# event_data = base64.b64decode(cloud_event.data['message']['data']).decode()
	event_attributes = cloud_event.data['message']['attributes']

	if not hasattr(main, 'env_vars'):
		env_vars = _env_vars()

	if not hasattr(main, 'gcp_clients'):
		gcp_clients = load_clients(gcp_project_id=env_vars.gcp_project_id)

	path = Path('./resources/staging_to_facts.sql')

	query = common.load_query(
		table_facts=env_vars.bq_facts_table_fqn,
		table_raw=env_vars.bq_staging_table_fqn,
		query_path=path,
		run_hash=event_attributes['closer-run-hash'],
	)

	_ = gcp_apis.execute_query_result(
		BQ=gcp_clients.bigquery_client,
		query=query,
	)

	gcp_apis.pubsub_publish_message(
		PS=gcp_clients.publisher,  # type: ignore
		project_id=env_vars.gcp_project_id,  # type: ignore
		topic_id=env_vars.topic_update_facts_complete,  # type: ignore
		message=json.dumps({'message': 'I finished passing the staging data to facts', 'training_data_table': env_vars.bq_facts_table_fqn}),
		attributes={'train_model': 'True', 'dataset': 'titanic'},
	)
