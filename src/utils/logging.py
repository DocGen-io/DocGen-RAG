import os
import warnings

import logging

def configure_logging():
    """
    Configures environment variables and warning filters to silence unnecessary logs and warnings.
    Must be called before importing libraries that rely on these environment variables.
    """
    os.environ.update({
        "GRPC_VERBOSITY": "ERROR",
        "GLOG_minloglevel": "2"
    })

    logging.captureWarnings(True)
    warnings.filterwarnings("ignore", category=ResourceWarning)
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="alembic")

    try:
        from sqlalchemy import exc as sa_exc
        warnings.filterwarnings("ignore", category=sa_exc.SAWarning)
    except ImportError:
        pass