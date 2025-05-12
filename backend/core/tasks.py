from celery import shared_task
import time
from django.utils import timezone # For setting timestamps

# Import models needed for updating ScanJob and creating ScanResult
from .models import ScanJob, ScanResult, ScanJobStatus, SecurityTool

@shared_task(name="core.example_task")
def example_task(x, y):
    print(f"Running example_task with arguments: {x}, {y}")
    time.sleep(5) # Simulate some work
    result = x + y
    print(f"Example task finished. Result: {result}")
    return result

@shared_task(name="core.another_example_task", bind=True, ignore_result=False)
def another_example_task(self, message):
    print(f"Task ID: {self.request.id}")
    print(f"Received message: {message}")
    time.sleep(2)
    return f"Processed: {message}"

# More tasks related to the 'core' app can be added here later.
# For example, tasks related to user notifications, data processing, etc.

@shared_task(name="core.simulate_bandit_scan", bind=True) # Added bind=True for self.request.id
def simulate_bandit_scan(self, target_info: dict, scan_job_id: int):
    """
    Simulates running a Bandit scan on a given target.
    Updates ScanJob status and creates ScanResult.
    target_info: A dictionary, e.g., {'type': 'file_path', 'value': '/path/to/code'}
    scan_job_id: The ID of the ScanJob this task is processing.
    """
    print(f"[SCAN TASK STARTED] Celery Task ID: {self.request.id}, ScanJob ID: {scan_job_id}, Target: {target_info}")
    
    scan_job = None
    try:
        scan_job = ScanJob.objects.get(pk=scan_job_id)
        scan_job.status = ScanJobStatus.RUNNING
        scan_job.started_timestamp = timezone.now()
        scan_job.celery_task_id = self.request.id # Ensure celery_task_id is updated if it wasn't set prior or if task was retried with new id
        scan_job.save()
    except ScanJob.DoesNotExist:
        print(f"[SCAN TASK ERROR] ScanJob with ID {scan_job_id} not found. Aborting task.")
        # Optionally, raise an exception to mark the task as failed if this is critical
        return # Or raise an error
    except Exception as e:
        print(f"[SCAN TASK ERROR] Error updating ScanJob {scan_job_id} to RUNNING: {e}")
        # Decide if to proceed or fail the task. For now, we'll try to proceed if scan_job was fetched.
        if scan_job:
            scan_job.status = ScanJobStatus.FAILED # Mark as failed if we can't even update to RUNNING properly
            scan_job.completed_timestamp = timezone.now()
            scan_job.save()
        raise # Re-raise to mark Celery task as failed

    try:
        # Simulate tool execution time
        print(f"Simulating Bandit scan for ScanJob ID: {scan_job_id}...")
        time.sleep(10) # Simulate a 10-second scan
        
        # Simulate finding some results
        simulated_results_data = {
            'tool': 'Bandit', # This should ideally come from a SecurityTool model instance
            'target': target_info,
            'findings_count': 3,
            'severity_summary': {
                'HIGH': 1,
                'MEDIUM': 1,
                'LOW': 1
            },
            'issues': [
                {'severity': 'HIGH', 'cwe': 'CWE-79', 'description': 'Potential XSS vulnerability.', 'file': 'test.py', 'line': 10},
                {'severity': 'MEDIUM', 'cwe': 'CWE-22', 'description': 'Potential path traversal.', 'file': 'utils.py', 'line': 45},
                {'severity': 'LOW', 'cwe': 'CWE-200', 'description': 'Hardcoded password.', 'file': 'config.py', 'line': 5},
            ]
        }
        
        # Create ScanResult
        ScanResult.objects.create(
            scan_job=scan_job,
            tool_name=simulated_results_data['tool'],
            summary_data=simulated_results_data['severity_summary'],
            findings=simulated_results_data['issues']
            # raw_output could be added if simulated
        )

        # Update ScanJob to COMPLETED
        scan_job.status = ScanJobStatus.COMPLETED
        scan_job.completed_timestamp = timezone.now()
        scan_job.save()
        
        print(f"[SCAN TASK FINISHED] ScanJob ID: {scan_job_id}. Bandit simulation complete. Findings: {simulated_results_data['findings_count']}")
        return simulated_results_data # The Celery task result (can be ignored by caller if data is in ScanResult)

    except Exception as e:
        print(f"[SCAN TASK FAILED] ScanJob ID: {scan_job_id}. Error during Bandit simulation: {e}")
        if scan_job: # Ensure scan_job object exists
            scan_job.status = ScanJobStatus.FAILED
            scan_job.completed_timestamp = timezone.now()
            scan_job.save()
            # Create a ScanResult with error information
            ScanResult.objects.create(
                scan_job=scan_job,
                tool_name='Bandit', # Or a generic error source
                error_message=str(e),
                findings=[] # Empty findings on error
            )
        raise # Re-raise exception to mark Celery task as FAILED 

@shared_task(name="core.execute_scan_job", bind=True)
def execute_scan_job(self, scan_job_id: int):
    """
    Executes a scan based on the ScanJob configuration.
    Updates ScanJob status and creates ScanResult(s).
    scan_job_id: The ID of the ScanJob this task is processing.
    """
    task_id = self.request.id
    print(f"[SCAN JOB TASK STARTED] Celery Task ID: {task_id}, ScanJob ID: {scan_job_id}")
    
    scan_job = None
    try:
        scan_job = ScanJob.objects.select_related('scan_configuration__project').get(pk=scan_job_id)
        scan_job.status = ScanJobStatus.RUNNING
        scan_job.started_timestamp = timezone.now()
        scan_job.celery_task_id = task_id
        scan_job.save()
    except ScanJob.DoesNotExist:
        print(f"[SCAN JOB TASK ERROR] ScanJob ID {scan_job_id} not found. Aborting.")
        return # Task finishes, but no result indicates an issue.
    except Exception as e:
        print(f"[SCAN JOB TASK ERROR] Error updating ScanJob {scan_job_id} to RUNNING: {e}")
        if scan_job: # If scan_job was fetched, mark it as FAILED
            scan_job.status = ScanJobStatus.FAILED
            scan_job.completed_timestamp = timezone.now()
            scan_job.save(update_fields=['status', 'completed_timestamp'])
        # Re-raise to mark Celery task as FAILED. 
        # Depending on Celery settings, this might lead to retries.
        raise

    try:
        tool_name = "GenericToolSimulator"
        target_description = "N/A"

        if scan_job.scan_configuration:
            scan_config = scan_job.scan_configuration
            tool_name = scan_config.name # Use scan config name as a stand-in for tool info
            if scan_config.target_details_json and isinstance(scan_config.target_details_json, dict):
                target_description = scan_config.target_details_json.get('description', 'N/A')
            print(f"Using ScanConfiguration: {scan_config.name} for project {scan_config.project.name}")
        else:
            print(f"No ScanConfiguration linked to ScanJob ID: {scan_job_id}. Using generic simulation.")

        # Simulate tool execution time
        print(f"Simulating scan for ScanJob ID: {scan_job_id} with tool/config: {tool_name}...")
        time.sleep(15) # Simulate a 15-second scan
        
        simulated_findings = [
            {'severity': 'HIGH', 'description': f'Simulated high severity issue for {target_description}', 'details': 'Detail A'},
            {'severity': 'MEDIUM', 'description': f'Simulated medium severity issue for {target_description}', 'details': 'Detail B'},
        ]
        summary = {'HIGH': 1, 'MEDIUM': 1, 'LOW': 0}

        ScanResult.objects.create(
            scan_job=scan_job,
            tool_name=tool_name,
            summary_data=summary,
            findings=simulated_findings
        )

        scan_job.status = ScanJobStatus.COMPLETED
        scan_job.completed_timestamp = timezone.now()
        scan_job.save()
        
        print(f"[SCAN JOB TASK FINISHED] ScanJob ID: {scan_job_id}. Status: {scan_job.status}")
        return {"status": "success", "findings_count": len(simulated_findings)}

    except Exception as e:
        error_message = f"Error during scan execution for ScanJob ID {scan_job_id}: {e}"
        print(f"[SCAN JOB TASK FAILED] {error_message}")
        if scan_job:
            scan_job.status = ScanJobStatus.FAILED
            scan_job.completed_timestamp = timezone.now()
            scan_job.save(update_fields=['status', 'completed_timestamp'])
            ScanResult.objects.create(
                scan_job=scan_job,
                tool_name=tool_name if 'tool_name' in locals() else "GenericErrorReporter",
                error_message=error_message,
                findings=[]
            )
        raise # Re-raise to mark Celery task as FAILED 