from datetime import datetime, timedelta
from airflow import DAG
from airflow.models import Variable
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocSubmitPySparkJobOperator,
    DataprocCreateClusterOperator,
    DataprocDeleteClusterOperator
)
from airflow.operator.bash import BashOperator
from airflow.operator.python import PythonOperator
from airflow.utils.dates import days_ago
from airflow.models.param import Param

default_args = {
    'owner' : 'airflow',
    'depends_on_past' : False,
    'email_on_failure' : False,
    'email_on_retry' : False,
    'retries' : 1,
    'retry_delay' : timedelta(minutes=5)
}

dag = DAG(
    'batch_spark_job',
    default_args = default_args,
    description = " A DAG to run Spark job on Dataproc",
    schedule_interval = timedelta(days=1),
    start_date = datetime(2024,12,10),
    catchup = False,
    tags = ['dev'],
    params = {
        'execution_date': Param(default = 'NA', type = "string", description = "Execution date in yyyymmdd format")
    }
)

# Fetch configuration from Airflow Variables
config = Variable.get("cluster_details", deserialize_json=True)
CLUSTER_NAME = config['CLUSTER_NAME']
PROJECT_ID = config['PROJECT_ID']
REGION = config['REGION']

pyspark_job_file_path = "gs://airflow_projects_repo/airflow-project-2/spark-code/orders_data_process.py"

# Python function to get the execution date
def get_execution_date(ds_nodash, **kwargs):
    execution_date = kwargs['params'].get('execution_date','NA')
    if execution_date == 'NA':
        execution_date = ds_nodash
    return execution_date

# PythinOperator to call the get_execution_date function
get_execution_date_task = PythonOperator(
    task_id = "get_execution_date",
    python_callable = get_execution_date,
    provide_context = True,
    op_kwargs = {'ds_nodash':'{{ ds_nodash}}'},
    dag = dag
)

submit_pyspark_job = DataprocSubmitPySparkJobOperator(
    task_id = 'submit_pyspark_job',
    main = pyspark_job_file_path,
    arguments = ['--date={{ ti.xcom_pull(task_ids=\'get_execution_date\')}}'], # Passing date as an argument to the PySpark Script
    cluster_name = CLUSTER_NAME,
    region = REGION,
    project_id = PROJECT_ID,
    dag = dag
)

# Set the task dependencies
get_execution_date_task >> submit_pyspark_job