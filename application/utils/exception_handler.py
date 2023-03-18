# Utility script to handle exceptions and log output to txt files for debugging
# purposes.

import inspect
import logging
import sys
import traceback

# Might move in future. Custom exception for bad function call.
class NonCallableFunctionException(Exception):
    pass

def try_exec(func, *args):
    """
    Executes the passed function within a try-except block.
    If an exception occurs, the error message is handled and 
    logged to output files for debugging.
    Ex: try_exec(sms_service.send_message, list(CAMERAS.keys())[idx], current_time, FEED_URL, filepath)

    :param func: function to execute within try-except.
    :param *args: arguments to pass when executing func.
    :return: a tuple with return code and results from func.
    """
    results = []
    try:
        if not callable(func):
            raise NonCallableFunctionException(func)
        results = func(*args)
    except NonCallableFunctionException as e:
        log_exception(e)

        stack_trace = traceback.format_exc()
        stack_trace = stack_trace[stack_trace.find("\n") + 1:]

        callingframe = sys._getframe(1)
        output = """Traceback (most recent call last):\n  File \"{}\", line {}, in {}\n    {}\n{}
            """.format(inspect.stack()[1].filename,
                       inspect.currentframe().f_back.f_lineno,
                       callingframe.f_code.co_name,
                       inspect.getframeinfo(inspect.currentframe().f_back).code_context[0].strip(),
                       stack_trace
                      )

        # Send alert to system admins. Need to fix.
        # sms_service.send_message(output)
        return -1, results
    except Exception as e:
        # Log output to log file for debugging purposes.
        log_exception(e)
        return 1, results
    return 0, results

def log_exception(data):
    # Write to log as an exception occurred.
    logger = logging.getLogger("Rotating Log")
    logger.exception(data)
