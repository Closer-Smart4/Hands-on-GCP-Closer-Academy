# Create an endpoint to serve the model to the outside world

![img-prediction-architecture](./resources/part_4/architecture-Step4.drawio.svg)

In this exercise, you'll be working with the `predictions_endpoint` Cloud Function. This HTTP-triggered function serves as the prediction endpoint for clients to send new data points. Upon receiving a request containing new data, the function performs the following steps:

1. It loads the previously trained model from the `[yourname]-models` bucket into memory.
2. Utilizing the loaded model, it generates a prediction based on a data point received in an HTTP request.
3. The function then stores both the prediction and the new data in the `Titanic Prediction` BigQuery table to maintain a record of all predictions.
4. Finally, it returns the prediction result to the client, completing the request-response cycle.

Your task is to create the resources necessary and deploy the function.

The outline of the *Cloud Function* code is available at `./functions/simple_mlops/d_predictions_endpoint/`

## Tasks

- [ ] Create the `Titanic Predictions` Table
  - The table is schema is at `resources/mlops_usecase/bigquery/titanic_predictions.json`
- [ ] Change the configurations in the `dev.env.yaml` file
- [ ] Change the deployment command to deploy the function correctly.


For Cloud Shell, set these variables:

```bash
export PROJECT_ID=$(gcloud config get-value project)
export PROJECT_NAME=$(gcloud config get-value project)
export REGION=europe-west3
export YOURNAME=your_name_in_lowercase
```

## Predictions table

```bash
bq mk \
    --project_id ${PROJECT_ID} \
    --table \
    --description "Facts table for the Titanic dataset" \
    --label=owner:${YOURNAME} \
    --label=project:${PROJECT_NAME} \
    --label=purpose:academy \
    --label=dataset:titanic \
    ${YOURNAME}_titanic.titanic_predictions \
    ./resources/mlops_usecase/bigquery/titanic_predictions.json
```

## Deployment

Deployment:

```bash
# Remeber to have $YOURNAME from the first export to the Cloud Shell. 
# Uncomment the next lines if you see necessary
# export REGION=europe-west3
# export YOURNAME=your_name_in_lowercase
export FUNCTION_NAME="predictions_endpoint"
export PATH_TO_FUNCTION="functions/mlops_usecase/d_predictions_endpoint"

gcloud beta functions deploy $YOURNAME-$FUNCTION_NAME \
    --gen2 --cpu=1 --memory=1024MB \
    --region=europe-west3 \
    --runtime=python311 \
    --source=${PATH_TO_FUNCTION}/app/ \
    --env-vars-file=${PATH_TO_FUNCTION}/config/dev.env.yaml \
    --allow-unauthenticated \
    --entry-point=predict \
    --trigger-http
```

And then you can test it on [on Stackblitz](https://stackblitz.com/edit/closer-gcp-titanic-frontend-example?file=src%2Fapp%2Ftitanic-prediction.service.ts) and change the `TitanicEndpoint` variable in `./src/app/titanic-prediction.service.ts`.

If all goes ok, you should receive the predictions in the frontend application, and they should be written to the `titanic_predictions` BigQuery table.

## Documentation

::: mlops_usecase.d_predictions_endpoint.app.main

::: mlops_usecase.d_predictions_endpoint.app.funcs.gcp_apis

::: mlops_usecase.d_predictions_endpoint.app.funcs.models
