import os
from fastapi import Depends, HTTPException, Body
from kubernetes import config
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

load_dotenv()

kubeconfig = os.environ.get("KUBE_CONFIG")

class K8sFile(BaseModel):
    file_name: str
    content: str

def load_kube_config():
    """Load kubernetes configuration in cluster"""
    try:
        config.load_incluster_config()
    except Exception as e:
        # 실패하면 kubeconfig 파일을 사용
        if kubeconfig:
            config.load_kube_config(config_file=kubeconfig)
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to load kubeconfig: {str(e)}"
            )
        
load_kube_config()