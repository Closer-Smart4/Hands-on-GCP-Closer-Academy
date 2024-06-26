import json
import os

import functions_framework
from cloudevents.http import CloudEvent
from google.cloud import bigquery, storage

try:
	from funcs import common, gcp_apis, models, train_models
except ImportError:
	from c_train_model.app.funcs import (
		common,
		gcp_apis,
		models,
		train_models,
	)


def load_clients(gcp_project_id: str) -> models.GCPClients:
	"""Load the GCP clients.

	Args:
	    gcp_project_id (str): The GCP project ID.

	Returns:
	    GCPClients: A tuple of GCP clients.
	        With the following attributes:
	            storage_client: A storage client.
	            bigquery_client: A bigquery client.
	"""
	storage_client = storage.Client(project=gcp_project_id)
	bigquery_client = bigquery.Client(project=gcp_project_id)

	return models.GCPClients(storage_client=storage_client, bigquery_client=bigquery_client)


##############################
# 1. Environment variables ###
##############################


def _env_vars() -> models.EnvVars:
	"""Load the environment variables.

	This function loads the environment variables required for the application to run. It returns a tuple of environment variables.

	Returns:
	    models.EnvVars: A tuple of environment variables.
	"""
	# fqn = fully qualified name
	# A table fqn is in the format: project_id.dataset_id.table_id

	return models.EnvVars(
		gcp_project_id=os.getenv('_GCP_PROJECT_ID', 'gcp_project_id'),
		bucket_name=os.getenv('_GCS_BUCKET_NAME_MODELS', 'bucket_name'),
		topic_training_complete=os.getenv('TOPIC_TRAINING_COMPLETE', 'topic_training_complete'),
	)


if os.getenv('_CI_TESTING', 'no') == 'no':
	env_vars = _env_vars()
	gcp_clients = load_clients(gcp_project_id=env_vars.gcp_project_id)


@functions_framework.cloud_event
def main(cloud_event: CloudEvent) -> None:
	"""Entrypoint of the cloud function."""
	if not hasattr(main, 'env_vars'):
		env_vars = _env_vars()

	if not hasattr(main, 'gcp_clients'):
		gcp_clients = load_clients(gcp_project_id=env_vars.gcp_project_id)

	event_message: dict = cloud_event.get_data()  # type: ignore

	data = json.loads(common.decode_base64_to_string(event_message['message']['data']))

	# Train the model
	if event_message['message']['attributes']['train_model'] == 'True':
		path = common.get_path_to_file()

		query = common.query_train_data(
			table_fqn=data['training_data_table'],  # type: ignore
			query_path=path,
		)
		df = gcp_apis.query_to_pandas_dataframe(
			query=query,
			BQ=gcp_clients.bigquery_client,  # type: ignore
		)

		pipeline = train_models.titanic_train(
			df=df,
		)

		gcp_apis.model_save_to_storage(
			CS=gcp_clients.storage_client,
			model=pipeline,
			bucket_name=env_vars.bucket_name,
		)
