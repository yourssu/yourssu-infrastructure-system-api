# app/services/kubernetes.py
from fastapi import HTTPException
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.client import V1Deployment, V1Service, V1Ingress
from kubernetes.client.api.apps_v1_api import AppsV1Api
from kubernetes.client.api.core_v1_api import CoreV1Api
from kubernetes.client.api.networking_v1_api import NetworkingV1Api
from typing import List, Optional
from datetime import datetime, timezone
from io import StringIO
import yaml
import time

from schemas.deployment_status import DeploymentStatus, PodStatus
from schemas.manifests import ManifestBase
from models.models import Deployment, Application

class KubernetesService:
    def __init__(self):
        # kubeconfig 파일이 있는 경우 로드
        try:
            config.load_kube_config()
        except:
            # kubeconfig 파일이 없는 경우 클러스터 내부에서 실행 중인 것으로 간주
            config.load_incluster_config()
        
        # API 클라이언트 인스턴스 생성
        self.apps_v1: AppsV1Api = client.AppsV1Api()
        self.core_v1: CoreV1Api = client.CoreV1Api()
        self.networking_v1: NetworkingV1Api = client.NetworkingV1Api()
        
        # 클라이언트 설정
        self._configure_client()
    
    def _configure_client(self):
        """Kubernetes 클라이언트 설정을 구성합니다."""
        # 전역 설정
        client.Configuration().retries = 3  # 재시도 횟수
        client.Configuration().timeout = 30  # 타임아웃 (초)
        
        # 연결 풀 설정
        client.Configuration().pool_connections = 20  # 연결 풀 크기
        client.Configuration().pool_maxsize = 20  # 최대 연결 수
        client.Configuration().pool_block = True  # 연결 풀이 가득 찼을 때 대기
    
    def _get_deployment(self, name: str, namespace: str) -> Optional[V1Deployment]:
        """Deployment 정보를 조회합니다."""
        try:
            return self.apps_v1.read_namespaced_deployment(
                name=name,
                namespace=namespace,
                _request_timeout=30  # 개별 요청 타임아웃
            )
        except ApiException as e:
            if e.status == 404:
                return None
            raise e

    def _get_service(self, name: str, namespace: str) -> Optional[V1Service]:
        """Service 정보를 조회합니다."""
        try:
            return self.core_v1.read_namespaced_service(
                name=name,
                namespace=namespace,
                _request_timeout=30
            )
        except ApiException as e:
            if e.status == 404:
                return None
            raise e

    def _get_ingress(self, name: str, namespace: str) -> Optional[V1Ingress]:
        """Ingress 정보를 조회합니다."""
        try:
            return self.networking_v1.read_namespaced_ingress(
                name=name,
                namespace=namespace,
                _request_timeout=30
            )
        except ApiException as e:
            if e.status == 404:
                return None
            raise e

    def apply_k8s(self, manifests: List[ManifestBase]):
        """
        쿠버네티스 클러스터에 YAML manifest를 적용합니다.
        
        Args:
            manifests (List[ManifestBase]): 적용할 manifest 리스트
            
        Raises:
            HTTPException: manifest 적용 실패 시
        """
        try:
            applied_files = []
            # manifest를 종류별로 분류
            namespace_manifests = []
            service_manifests = []
            deployment_manifests = []
            ingress_manifests = []
            other_manifests = []
            
            for manifest in manifests:
                content = yaml.safe_load(manifest.content)
                kind = content.get("kind", "").lower()
                
                if kind == "namespace":
                    namespace_manifests.append(manifest)
                elif kind == "service":
                    service_manifests.append(manifest)
                elif kind == "deployment":
                    deployment_manifests.append(manifest)
                elif kind == "ingress":
                    ingress_manifests.append(manifest)
                else:
                    other_manifests.append(manifest)
            
            # 순서대로 적용
            for manifest in namespace_manifests:
                try:
                    self._apply_yaml_content(manifest.content)
                    applied_files.append(manifest.file_name)
                except ApiException as e:
                    if e.status == 403:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"Permission denied: {str(e)}"
                        )
                    elif e.status == 409:
                        raise HTTPException(
                            status_code=409, 
                            detail=f"Resource conflict: {str(e)}"
                        )
                    else:
                        raise HTTPException(
                            status_code=500, 
                            detail=f"Failed to apply {manifest.file_name}: {str(e)}"
                        )
            
            # Service 적용
            for manifest in service_manifests:
                try:
                    self._apply_yaml_content(manifest.content)
                    applied_files.append(manifest.file_name)
                except ApiException as e:
                    if e.status == 403:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"Permission denied: {str(e)}"
                        )
                    elif e.status == 409:
                        raise HTTPException(
                            status_code=409, 
                            detail=f"Resource conflict: {str(e)}"
                        )
                    else:
                        raise HTTPException(
                            status_code=500, 
                            detail=f"Failed to apply {manifest.file_name}: {str(e)}"
                        )
            
            # Deployment 적용
            for manifest in deployment_manifests:
                try:
                    self._apply_yaml_content(manifest.content)
                    applied_files.append(manifest.file_name)
                except ApiException as e:
                    if e.status == 403:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"Permission denied: {str(e)}"
                        )
                    elif e.status == 409:
                        raise HTTPException(
                            status_code=409, 
                            detail=f"Resource conflict: {str(e)}"
                        )
                    else:
                        raise HTTPException(
                            status_code=500, 
                            detail=f"Failed to apply {manifest.file_name}: {str(e)}"
                        )
            
            # Ingress 적용
            for manifest in ingress_manifests:
                try:
                    self._apply_yaml_content(manifest.content)
                    applied_files.append(manifest.file_name)
                except ApiException as e:
                    if e.status == 403:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"Permission denied: {str(e)}"
                        )
                    elif e.status == 409:
                        raise HTTPException(
                            status_code=409, 
                            detail=f"Resource conflict: {str(e)}"
                        )
                    else:
                        raise HTTPException(
                            status_code=500, 
                            detail=f"Failed to apply {manifest.file_name}: {str(e)}"
                        )
            
            # 나머지 리소스 적용
            for manifest in other_manifests:
                try:
                    self._apply_yaml_content(manifest.content)
                    applied_files.append(manifest.file_name)
                except ApiException as e:
                    if e.status == 403:
                        raise HTTPException(
                            status_code=403, 
                            detail=f"Permission denied: {str(e)}"
                        )
                    elif e.status == 409:
                        raise HTTPException(
                            status_code=409, 
                            detail=f"Resource conflict: {str(e)}"
                        )
                    else:
                        raise HTTPException(
                            status_code=500, 
                            detail=f"Failed to apply {manifest.file_name}: {str(e)}"
                        )
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to apply manifests: {str(e)}"
            )
        finally:
            print(f"Applied K8S Resources: {applied_files}")

    def delete_k8s(self, manifests: List[ManifestBase]):
        """
        쿠버네티스 클러스터에서 YAML manifest를 삭제합니다.
        
        Args:
            manifests (List[ManifestBase]): 삭제할 manifest 리스트
            
        Raises:
            HTTPException: manifest 삭제 실패 시
        """
        try:
            # manifest를 종류별로 분류
            namespace_manifests = []
            service_manifests = []
            deployment_manifests = []
            ingress_manifests = []
            other_manifests = []
            
            for manifest in manifests:
                content = yaml.safe_load(manifest.content)
                kind = content.get("kind", "").lower()
                
                if kind == "namespace":
                    namespace_manifests.append(manifest)
                elif kind == "service":
                    service_manifests.append(manifest)
                elif kind == "deployment":
                    deployment_manifests.append(manifest)
                elif kind == "ingress":
                    ingress_manifests.append(manifest)
                else:
                    other_manifests.append(manifest)

            # 삭제 순서: deployment -> service -> ingress -> namespace -> other
            for manifest in deployment_manifests:
                content = yaml.safe_load(manifest.content)
                name = content.get("metadata", {}).get("name")
                namespace = content.get("metadata", {}).get("namespace", "default")
                
                try:
                    self.apps_v1.delete_namespaced_deployment(
                        name=name,
                        namespace=namespace
                    )
                except Exception as e:
                    if "not found" not in str(e).lower():
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to delete deployment {name}: {str(e)}"
                        )

            for manifest in service_manifests:
                content = yaml.safe_load(manifest.content)
                name = content.get("metadata", {}).get("name")
                namespace = content.get("metadata", {}).get("namespace", "default")
                
                try:
                    self.core_v1.delete_namespaced_service(
                        name=name,
                        namespace=namespace
                    )
                except Exception as e:
                    if "not found" not in str(e).lower():
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to delete service {name}: {str(e)}"
                        )

            for manifest in ingress_manifests:
                content = yaml.safe_load(manifest.content)
                name = content.get("metadata", {}).get("name")
                namespace = content.get("metadata", {}).get("namespace", "default")
                
                try:
                    self.networking_v1.delete_namespaced_ingress(
                        name=name,
                        namespace=namespace
                    )
                except Exception as e:
                    if "not found" not in str(e).lower():
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to delete ingress {name}: {str(e)}"
                        )

            for manifest in namespace_manifests:
                content = yaml.safe_load(manifest.content)
                name = content.get("metadata", {}).get("name")
                
                try:
                    self.core_v1.delete_namespace(name=name)
                except Exception as e:
                    if "not found" not in str(e).lower():
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to delete namespace {name}: {str(e)}"
                        )

            for manifest in other_manifests:
                content = yaml.safe_load(manifest.content)
                kind = content.get("kind", "").lower()
                name = content.get("metadata", {}).get("name")
                namespace = content.get("metadata", {}).get("namespace", "default")
                
                try:
                    if kind == "configmap":
                        self.core_v1.delete_namespaced_config_map(
                            name=name,
                            namespace=namespace
                        )
                    elif kind == "secret":
                        self.core_v1.delete_namespaced_secret(
                            name=name,
                            namespace=namespace
                        )
                    # 필요한 다른 리소스 타입에 대한 삭제 로직 추가
                except Exception as e:
                    if "not found" not in str(e).lower():
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to delete {kind} {name}: {str(e)}"
                        )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete manifests: {str(e)}"
            )

    def create_deployment_manifests(self, latest_deployment: Deployment, new_image_url: str) -> List[ManifestBase]:
        """
        기존 deployment를 템플릿으로 사용하여 새로운 manifest 리스트를 생성합니다.
        
        Args:
            latest_deployment (Deployment): 템플릿으로 사용할 가장 최근 Deployment 객체
            new_image_url (str): 새로운 이미지 URL
            
        Returns:
            List[ManifestBase]: 업데이트된 manifest 리스트
        """
        try:
            new_manifests = []
            for manifest in latest_deployment.manifests:
                content = yaml.safe_load(manifest.content)
                if content.get("kind", "").lower() == "deployment":
                    # Deployment manifest의 이미지 URL 업데이트
                    containers = content.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
                    if not containers:
                        raise HTTPException(
                            status_code=400,
                            detail="No containers found in deployment manifest"
                        )
                    containers[0]["image"] = new_image_url
                    new_content = yaml.dump(content)
                else:
                    # 다른 manifest는 그대로 복사
                    new_content = manifest.content

                new_manifests.append(
                    ManifestBase(
                        file_name=manifest.file_name,
                        content=new_content
                    )
                )
            
            return new_manifests

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create deployment manifests: {str(e)}"
            )

    def apply_deployment_update(self, deployment: Deployment, new_image_url: str):
        """
        새로운 이미지로 deployment를 업데이트하고 즉시 적용합니다.
        
        Args:
            deployment (Deployment): 업데이트할 Deployment 객체
            new_image_url (str): 새로운 이미지 URL
            
        Returns:
            List[ManifestBase]: 적용된 manifest 리스트
        """
        # 새로운 manifest 생성
        new_manifests = self.create_deployment_manifests(deployment, new_image_url)
        
        # 클러스터에 즉시 적용
        self.apply_k8s(new_manifests)
        
        return new_manifests

    def update_deployment_image(self, deployment: Deployment, new_image_url: str):
        """
        Deployment의 이미지를 업데이트합니다.
        
        Args:
            deployment (Deployment): 업데이트할 Deployment 객체
            new_image_url (str): 새로운 이미지 URL
        """
        try:
            # Deployment manifest 찾기
            deployment_manifest = None
            for manifest in deployment.manifests:
                content = yaml.safe_load(manifest.content)
                if content.get("kind", "").lower() == "deployment":
                    deployment_manifest = manifest
                    break
            
            if not deployment_manifest:
                raise HTTPException(
                    status_code=404,
                    detail="Deployment manifest not found"
                )

            # Manifest 내용 업데이트
            content = yaml.safe_load(deployment_manifest.content)
            containers = content.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
            
            if not containers:
                raise HTTPException(
                    status_code=400,
                    detail="No containers found in deployment manifest"
                )

            # 컨테이너 이미지 업데이트
            containers[0]["image"] = new_image_url
            deployment_manifest.content = yaml.dump(content)

            # 업데이트된 manifest 적용
            self.apply_k8s([
                ManifestBase(
                    file_name=manifest.file_name,
                    content=manifest.content
                ) for manifest in deployment.manifests
            ])

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update deployment image: {str(e)}"
            )

    def get_application_status(self, application_id: int, deployment_name: str, namespace: str = "default") -> DeploymentStatus:
        """
        특정 Application의 배포 상태를 조회합니다.
        
        Args:
            application_id (int): Application ID
            deployment_name (str): 조회할 Deployment 이름
            namespace (str): Kubernetes namespace (기본값: "default")
            
        Returns:
            DeploymentStatus: Deployment의 상태 정보
            
        Raises:
            HTTPException: Deployment를 찾을 수 없거나 API 호출 중 오류 발생 시
        """
        try:
            print(f"Getting deployment status for {deployment_name} in namespace {namespace}")
            # Deployment 정보 조회
            deployment = self._get_deployment(deployment_name, namespace)
            print(f"Successfully got deployment info for {deployment_name}")
            
            # Deployment에 속한 Pod 정보 조회
            pod_statuses = self._get_pod_statuses(deployment_name, namespace)
            print(f"Successfully got pod statuses for {deployment_name}")
            
            return DeploymentStatus(
                application_id=application_id,
                name=deployment.metadata.name,
                ready_replicas=deployment.status.ready_replicas or 0,
                total_replicas=deployment.status.replicas or 0,
                available_replicas=deployment.status.available_replicas or 0,
                updated_replicas=deployment.status.updated_replicas or 0,
                conditions=[{
                    'type': condition.type,
                    'status': condition.status,
                    'reason': condition.reason,
                    'message': condition.message,
                    'last_update': condition.last_update_time.isoformat() if condition.last_update_time else None,
                } for condition in deployment.status.conditions] if deployment.status.conditions else [],
                pods=pod_statuses,
                age=self._calculate_age(deployment.metadata.creation_timestamp)
            )
            
        except client.ApiException as e:
            print(f"API Exception for deployment {deployment_name}: {str(e)}")
            self._handle_api_exception(e, f"Deployment {deployment_name}")
        except Exception as e:
            print(f"Unexpected error for deployment {deployment_name}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get deployment status: {str(e)}"
            )

    def get_all_applications_status(self, applications: List[Application]) -> List[DeploymentStatus]:
        """
        모든 Deployment의 상태를 조회합니다.
        각 Deployment는 해당 Application의 이름을 namespace로 사용합니다.
        """
        try:
            application_statuses = []
            for application in applications:
                try:
                    print(f"Attempting to get status for application: {application.name}")
                    # application.name을 namespace로 사용
                    status = self.get_application_status(
                        application_id=application.id,
                        deployment_name=application.name,
                        namespace=application.name
                    )
                    application_statuses.append(status)
                    print(f"Successfully got status for application: {application.name}")
                except HTTPException as e:
                    # 개별 deployment 조회 실패 시 해당 deployment는 건너뛰고 계속 진행
                    print(f"Failed to get status for deployment {application.name}: {str(e)}")
                    continue
                except Exception as e:
                    print(f"Unexpected error for deployment {application.name}: {str(e)}")
                    continue
                    
            return application_statuses
            
        except Exception as e:
            print(f"Failed to get deployments status: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get deployments status: {str(e)}"
            )

    def get_application_status_by_id(self, application: Application) -> DeploymentStatus:
        """
        특정 Deployment ID로 상태를 조회합니다.
        
        Args:
            application (Application): Application
            
        Returns:
            DeploymentStatus: Deployment의 상태 정보
            
        Raises:
            HTTPException: Deployment를 찾을 수 없거나 API 호출 중 오류 발생 시
        """
            
        return self.get_application_status(
            application_id=application.id,
            deployment_name=application.name,
            namespace=application.name
        )

    def _apply_yaml_content(self, yaml_content: str):
        """YAML content를 파싱하고 쿠버네티스에 적용합니다."""
        obj = yaml.safe_load(yaml_content)
        if not obj:
            return
        
        kind = obj.get("kind", "")
        api_version = obj.get("apiVersion", "")
        metadata = obj.get("metadata", {})
        name = metadata.get("name", "")
        namespace = metadata.get("namespace", "default")
        
        group, _, version = api_version.partition("/")
        if not version:
            version = group
            group = "core"
        
        plural = f"{kind.lower()}s"
        is_namespaced = kind.lower() not in [
            "persistentvolume", "clusterrole", "clusterrolebinding", 
            "customresourcedefinition", "node", "storageclass",
            "namespace"
        ]
        
        self._apply_resource(
            group=group,
            version=version,
            plural=plural,
            name=name,
            namespace=namespace,
            body=obj,
            is_namespaced=is_namespaced,
            kind=kind
        )

    def _apply_resource(self, group: str, version: str, plural: str, 
                       name: str, namespace: str, body: dict, is_namespaced: bool,
                       kind: str):
        """리소스를 생성하거나 업데이트합니다."""
        try:
            if kind.lower() == "namespace":
                # 네임스페이스는 core API를 사용
                try:
                    self.core_v1.read_namespace(name=name)
                    self.core_v1.patch_namespace(name=name, body=body)
                except ApiException as e:
                    if e.status == 404:
                        namespace_body = {
                            "apiVersion": "v1",
                            "kind": "Namespace",
                            "metadata": {
                                "name": name
                            }
                        }
                        self.core_v1.create_namespace(body=namespace_body)
                    else:
                        raise
            elif kind.lower() == "service":
                # 서비스는 core API를 사용
                try:
                    self.core_v1.read_namespaced_service(name=name, namespace=namespace)
                    self.core_v1.patch_namespaced_service(name=name, namespace=namespace, body=body)
                except ApiException as e:
                    if e.status == 404:
                        self.core_v1.create_namespaced_service(namespace=namespace, body=body)
                    else:
                        raise
            elif kind.lower() == "deployment":
                # 디플로이먼트는 apps API를 사용
                try:
                    self.apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
                    self.apps_v1.patch_namespaced_deployment(name=name, namespace=namespace, body=body)
                except ApiException as e:
                    if e.status == 404:
                        self.apps_v1.create_namespaced_deployment(namespace=namespace, body=body)
                    else:
                        raise
            elif kind.lower() == "ingress":
                # 인그레스는 networking API를 사용
                try:
                    self.networking_v1.read_namespaced_ingress(name=name, namespace=namespace)
                    self.networking_v1.patch_namespaced_ingress(name=name, namespace=namespace, body=body)
                except ApiException as e:
                    if e.status == 404:
                        self.networking_v1.create_namespaced_ingress(namespace=namespace, body=body)
                    else:
                        raise
            else:
                # 그 외 리소스는 custom objects API를 사용
                try:
                    self.custom_objects.get_namespaced_custom_object(
                        group=group, version=version,
                        namespace=namespace, plural=plural, name=name
                    )
                    self.custom_objects.patch_namespaced_custom_object(
                        group=group, version=version,
                        namespace=namespace, plural=plural, name=name, body=body
                    )
                except ApiException as e:
                    if e.status == 404:
                        self.custom_objects.create_namespaced_custom_object(
                            group=group, version=version,
                            namespace=namespace, plural=plural, body=body
                        )
                    else:
                        raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to apply resource {name}: {str(e)}"
            )
        
    def _get_pod_statuses(self, deployment_name: str, namespace: str) -> List[PodStatus]:
        """Deployment에 속한 Pod들의 상태를 조회합니다."""
        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace=namespace,
                label_selector=f"app={deployment_name}",
                _request_timeout=30
            )
            
            return [
                self._create_pod_status(pod)
                for pod in pods.items
            ]
        except ApiException as e:
            if e.status == 404:
                return []
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get pod statuses: {str(e)}"
            )

    def _create_pod_status(self, pod) -> PodStatus:
        """Pod 정보로부터 PodStatus 객체를 생성합니다."""
        container_statuses = pod.status.container_statuses or []
        
        return PodStatus(
            name=pod.metadata.name,
            ready=all(container.ready for container in container_statuses),
            status=pod.status.phase,
            restarts=sum(container.restart_count for container in container_statuses),
            age=self._calculate_age(pod.metadata.creation_timestamp)
        )

    def _calculate_age(self, creation_timestamp: datetime) -> str:
        """리소스의 생성 시간으로부터 경과 시간을 계산합니다."""
        if not creation_timestamp:
            return "Unknown"
            
        now = datetime.now(timezone.utc)
        age = now - creation_timestamp
        
        days = age.days
        hours = age.seconds // 3600
        minutes = (age.seconds % 3600) // 60
        
        if days > 0:
            return f"{days}d"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}m"

    def _handle_api_exception(self, e: client.ApiException, resource: str):
        """Kubernetes API 예외를 처리합니다."""
        if e.status == 404:
            raise HTTPException(
                status_code=404,
                detail=f"{resource} not found"
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get {resource.lower()} status: {str(e)}"
        )

    def _wait_for_resource_ready(self, yaml_data: dict, timeout: int = 300):
        """리소스가 준비될 때까지 대기합니다."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if yaml_data["kind"] == "Deployment":
                    deployment = self._get_deployment(
                        name=yaml_data["metadata"]["name"],
                        namespace=yaml_data["metadata"]["namespace"]
                    )
                    if deployment and deployment.status.ready_replicas == deployment.status.replicas:
                        return
                elif yaml_data["kind"] == "Service":
                    service = self._get_service(
                        name=yaml_data["metadata"]["name"],
                        namespace=yaml_data["metadata"]["namespace"]
                    )
                    if service:
                        return
                elif yaml_data["kind"] == "Ingress":
                    ingress = self._get_ingress(
                        name=yaml_data["metadata"]["name"],
                        namespace=yaml_data["metadata"]["namespace"]
                    )
                    if ingress:
                        return
            except ApiException:
                pass
            time.sleep(5)
        raise TimeoutError(f"Resource {yaml_data['metadata']['name']} not ready after {timeout} seconds")