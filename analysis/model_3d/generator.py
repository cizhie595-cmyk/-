"""
3D 动态商品描述生成模块

利用 AI 3D 建模 API 将商品 2D 图片转换为 3D 模型，
用于前端展示和增强商品描述。

支持的 3D 生成引擎：
  - Meshy AI: 图片转3D、文字转3D
  - Tripo AI: 高精度图片转3D
  - 本地 Three.js 渲染预览

工作流程：
  1. 从商品详情页提取主图
  2. 调用 3D 生成 API 将图片转为 3D 模型（GLB/OBJ 格式）
  3. 存储模型文件并生成 Three.js 预览页面
  4. 在前端以交互式 3D 视图展示商品
"""

import os
import time
import json
from typing import Optional
from enum import Enum

import requests

from utils.logger import get_logger

logger = get_logger()


class ModelFormat(str, Enum):
    """3D 模型格式"""
    GLB = "glb"
    OBJ = "obj"
    FBX = "fbx"
    STL = "stl"
    USDZ = "usdz"


class MeshyClient:
    """
    Meshy AI 3D 生成客户端

    API 文档: https://docs.meshy.ai/
    支持:
      - Image to 3D: 从产品图片生成 3D 模型
      - Text to 3D: 从文字描述生成 3D 模型
      - Text to Texture: 为 3D 模型生成纹理
    """

    BASE_URL = "https://api.meshy.ai/v2"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def image_to_3d(self, image_url: str,
                    topology: str = "quad",
                    target_polycount: int = 30000,
                    enable_texture: bool = True) -> Optional[dict]:
        """
        从产品图片生成 3D 模型。

        :param image_url: 产品图片 URL（公网可访问）
        :param topology: 拓扑类型 (quad / triangle)
        :param target_polycount: 目标面数
        :param enable_texture: 是否生成纹理
        :return: 任务信息 {"task_id": str, "status": str}
        """
        payload = {
            "image_url": image_url,
            "enable_pbr": enable_texture,
            "topology": topology,
            "target_polycount": target_polycount,
        }

        try:
            resp = requests.post(
                f"{self.BASE_URL}/image-to-3d",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            task_id = data.get("result")
            logger.info(f"[Meshy] Image-to-3D 任务已创建: {task_id}")
            return {"task_id": task_id, "status": "pending", "engine": "meshy"}

        except Exception as e:
            logger.error(f"[Meshy] Image-to-3D 创建失败: {e}")
            return None

    def text_to_3d(self, prompt: str, art_style: str = "realistic",
                   negative_prompt: str = "") -> Optional[dict]:
        """
        从文字描述生成 3D 模型。

        :param prompt: 3D 模型描述
        :param art_style: 风格 (realistic / cartoon / low-poly / sculpture)
        :param negative_prompt: 负面提示词
        :return: 任务信息
        """
        payload = {
            "mode": "preview",
            "prompt": prompt,
            "art_style": art_style,
            "negative_prompt": negative_prompt,
        }

        try:
            resp = requests.post(
                f"{self.BASE_URL}/text-to-3d",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            task_id = data.get("result")
            logger.info(f"[Meshy] Text-to-3D 任务已创建: {task_id}")
            return {"task_id": task_id, "status": "pending", "engine": "meshy"}

        except Exception as e:
            logger.error(f"[Meshy] Text-to-3D 创建失败: {e}")
            return None

    def get_task_status(self, task_id: str) -> dict:
        """查询任务状态"""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/image-to-3d/{task_id}",
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "task_id": task_id,
                "status": data.get("status", "unknown"),
                "progress": data.get("progress", 0),
                "model_urls": data.get("model_urls", {}),
                "thumbnail_url": data.get("thumbnail_url", ""),
            }

        except Exception as e:
            logger.error(f"[Meshy] 查询任务状态失败: {e}")
            return {"task_id": task_id, "status": "error", "error": str(e)}

    def wait_for_completion(self, task_id: str, timeout: int = 300,
                            poll_interval: int = 10) -> dict:
        """
        等待任务完成。

        :param task_id: 任务 ID
        :param timeout: 超时时间（秒）
        :param poll_interval: 轮询间隔（秒）
        :return: 最终任务状态
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)

            if status["status"] == "SUCCEEDED":
                logger.info(f"[Meshy] 任务完成: {task_id}")
                return status
            elif status["status"] in ("FAILED", "EXPIRED"):
                logger.error(f"[Meshy] 任务失败: {task_id} | {status}")
                return status

            progress = status.get("progress", 0)
            logger.info(f"[Meshy] 任务进行中: {task_id} | 进度: {progress}%")
            time.sleep(poll_interval)

        logger.warning(f"[Meshy] 任务超时: {task_id}")
        return {"task_id": task_id, "status": "timeout"}

    def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/image-to-3d",
                headers=self.headers,
                params={"limit": 1},
                timeout=10,
            )
            return resp.status_code in (200, 401, 403)
        except Exception:
            return False


class TripoClient:
    """
    Tripo AI 3D 生成客户端

    API 文档: https://platform.tripo3d.ai/docs
    支持:
      - Image to 3D: 高精度图片转3D
      - Text to 3D: 文字描述转3D
      - 模型优化和纹理增强
    """

    BASE_URL = "https://api.tripo3d.ai/v2/openapi"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def image_to_3d(self, image_token: str,
                    model_version: str = "v2.0-20240919") -> Optional[dict]:
        """
        从产品图片生成 3D 模型。

        :param image_token: 上传图片后获得的 token
        :param model_version: 模型版本
        :return: 任务信息
        """
        payload = {
            "type": "image_to_model",
            "file": {"type": "image", "file_token": image_token},
            "model_version": model_version,
        }

        try:
            resp = requests.post(
                f"{self.BASE_URL}/task",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            task_id = data.get("data", {}).get("task_id")
            logger.info(f"[Tripo] Image-to-3D 任务已创建: {task_id}")
            return {"task_id": task_id, "status": "pending", "engine": "tripo"}

        except Exception as e:
            logger.error(f"[Tripo] Image-to-3D 创建失败: {e}")
            return None

    def upload_image(self, image_path: str) -> Optional[str]:
        """
        上传图片获取 file_token。

        :param image_path: 本地图片路径
        :return: file_token
        """
        try:
            with open(image_path, "rb") as f:
                files = {"file": f}
                headers = {"Authorization": f"Bearer {self.api_key}"}
                resp = requests.post(
                    f"{self.BASE_URL}/upload",
                    headers=headers,
                    files=files,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("data", {}).get("image_token")

        except Exception as e:
            logger.error(f"[Tripo] 图片上传失败: {e}")
            return None

    def text_to_3d(self, prompt: str,
                   model_version: str = "v2.0-20240919") -> Optional[dict]:
        """从文字描述生成 3D 模型"""
        payload = {
            "type": "text_to_model",
            "prompt": prompt,
            "model_version": model_version,
        }

        try:
            resp = requests.post(
                f"{self.BASE_URL}/task",
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            task_id = data.get("data", {}).get("task_id")
            logger.info(f"[Tripo] Text-to-3D 任务已创建: {task_id}")
            return {"task_id": task_id, "status": "pending", "engine": "tripo"}

        except Exception as e:
            logger.error(f"[Tripo] Text-to-3D 创建失败: {e}")
            return None

    def get_task_status(self, task_id: str) -> dict:
        """查询任务状态"""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/task/{task_id}",
                headers=self.headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})

            return {
                "task_id": task_id,
                "status": data.get("status", "unknown"),
                "progress": data.get("progress", 0),
                "output": data.get("output", {}),
            }

        except Exception as e:
            logger.error(f"[Tripo] 查询任务状态失败: {e}")
            return {"task_id": task_id, "status": "error"}

    def wait_for_completion(self, task_id: str, timeout: int = 300,
                            poll_interval: int = 10) -> dict:
        """等待任务完成"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.get_task_status(task_id)

            if status["status"] == "success":
                logger.info(f"[Tripo] 任务完成: {task_id}")
                return status
            elif status["status"] in ("failed", "cancelled"):
                logger.error(f"[Tripo] 任务失败: {task_id}")
                return status

            logger.info(f"[Tripo] 任务进行中: {task_id} | 进度: {status.get('progress', 0)}%")
            time.sleep(poll_interval)

        return {"task_id": task_id, "status": "timeout"}

    def download_model(self, task_id: str, output_dir: str,
                       format: str = "glb") -> Optional[str]:
        """下载生成的 3D 模型文件"""
        status = self.get_task_status(task_id)
        output = status.get("output", {})
        model_url = output.get("model", "")

        if not model_url:
            logger.error(f"[Tripo] 无模型下载链接: {task_id}")
            return None

        try:
            os.makedirs(output_dir, exist_ok=True)
            filepath = os.path.join(output_dir, f"{task_id}.{format}")

            resp = requests.get(model_url, timeout=60)
            resp.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(resp.content)

            logger.info(f"[Tripo] 模型已下载: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"[Tripo] 模型下载失败: {e}")
            return None

    def test_connection(self) -> bool:
        """测试 API 连接"""
        try:
            resp = requests.get(
                f"{self.BASE_URL}/task",
                headers=self.headers,
                params={"page_num": 1, "page_size": 1},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False


class ThreeDGenerator:
    """
    3D 商品描述生成器（协调器）

    整合 Meshy 和 Tripo 两个引擎，
    自动选择最佳引擎生成 3D 模型，
    并生成 Three.js 预览页面。
    """

    def __init__(self, meshy_key: str = None, tripo_key: str = None,
                 output_dir: str = "data/3d_models",
                 preferred_engine: str = "meshy"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.meshy = MeshyClient(meshy_key) if meshy_key else None
        self.tripo = TripoClient(tripo_key) if tripo_key else None
        self.preferred_engine = preferred_engine

    def generate_from_image(self, image_url: str = None,
                            image_path: str = None,
                            asin: str = "") -> dict:
        """
        从商品图片生成 3D 模型。

        :param image_url: 图片 URL（用于 Meshy）
        :param image_path: 本地图片路径（用于 Tripo）
        :param asin: 商品 ASIN（用于文件命名）
        :return: 生成结果
        """
        result = {
            "asin": asin,
            "status": "pending",
            "engine": None,
            "model_path": None,
            "preview_url": None,
        }

        # 选择引擎
        if self.preferred_engine == "meshy" and self.meshy and image_url:
            result["engine"] = "meshy"
            task = self.meshy.image_to_3d(image_url)
            if task:
                final = self.meshy.wait_for_completion(task["task_id"])
                if final["status"] == "SUCCEEDED":
                    result["status"] = "success"
                    result["model_urls"] = final.get("model_urls", {})
                    result["thumbnail"] = final.get("thumbnail_url", "")
                    # 下载 GLB 模型
                    glb_url = result["model_urls"].get("glb", "")
                    if glb_url:
                        result["model_path"] = self._download_model(
                            glb_url, asin, "glb"
                        )
                else:
                    result["status"] = "failed"
                    result["error"] = final.get("status", "unknown error")

        elif self.tripo and image_path:
            result["engine"] = "tripo"
            token = self.tripo.upload_image(image_path)
            if token:
                task = self.tripo.image_to_3d(token)
                if task:
                    final = self.tripo.wait_for_completion(task["task_id"])
                    if final["status"] == "success":
                        result["status"] = "success"
                        model_path = self.tripo.download_model(
                            task["task_id"], self.output_dir
                        )
                        result["model_path"] = model_path
                    else:
                        result["status"] = "failed"

        else:
            result["status"] = "no_engine"
            result["error"] = "无可用的 3D 生成引擎，请配置 Meshy 或 Tripo API Key"

        # 生成 Three.js 预览页面
        if result["model_path"]:
            result["preview_url"] = self._generate_preview_page(
                result["model_path"], asin
            )

        return result

    def generate_from_text(self, description: str,
                           asin: str = "") -> dict:
        """从文字描述生成 3D 模型"""
        result = {
            "asin": asin,
            "status": "pending",
            "engine": None,
        }

        if self.meshy:
            result["engine"] = "meshy"
            task = self.meshy.text_to_3d(description)
            if task:
                final = self.meshy.wait_for_completion(task["task_id"])
                if final["status"] == "SUCCEEDED":
                    result["status"] = "success"
                    result["model_urls"] = final.get("model_urls", {})
                else:
                    result["status"] = "failed"

        elif self.tripo:
            result["engine"] = "tripo"
            task = self.tripo.text_to_3d(description)
            if task:
                final = self.tripo.wait_for_completion(task["task_id"])
                if final["status"] == "success":
                    result["status"] = "success"
                else:
                    result["status"] = "failed"

        return result

    def _download_model(self, url: str, asin: str, fmt: str) -> Optional[str]:
        """下载模型文件"""
        try:
            filepath = os.path.join(self.output_dir, f"{asin}.{fmt}")
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(resp.content)

            logger.info(f"[3D] 模型已下载: {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"[3D] 模型下载失败: {e}")
            return None

    def _generate_preview_page(self, model_path: str, asin: str) -> str:
        """
        生成 Three.js 3D 模型预览 HTML 页面。

        :param model_path: GLB 模型文件路径
        :param asin: 商品 ASIN
        :return: 预览页面路径
        """
        model_filename = os.path.basename(model_path)
        preview_path = os.path.join(self.output_dir, f"{asin}_preview.html")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Product View - {asin}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #1a1a2e; overflow: hidden; font-family: Arial, sans-serif; }}
        #canvas-container {{ width: 100vw; height: 100vh; }}
        .controls {{
            position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%);
            display: flex; gap: 12px; z-index: 100;
        }}
        .controls button {{
            padding: 10px 20px; border: none; border-radius: 8px;
            background: rgba(255,255,255,0.15); color: #fff;
            cursor: pointer; font-size: 14px; backdrop-filter: blur(10px);
            transition: background 0.3s;
        }}
        .controls button:hover {{ background: rgba(255,255,255,0.3); }}
        .info {{
            position: fixed; top: 20px; left: 20px; color: #fff;
            font-size: 13px; opacity: 0.7;
        }}
        .loading {{
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            color: #fff; font-size: 18px; z-index: 200;
        }}
        .loading .spinner {{
            width: 40px; height: 40px; border: 3px solid rgba(255,255,255,0.3);
            border-top-color: #fff; border-radius: 50%;
            animation: spin 1s linear infinite; margin: 0 auto 15px;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    </style>
</head>
<body>
    <div id="loading" class="loading">
        <div class="spinner"></div>
        <div>Loading 3D Model...</div>
    </div>
    <div id="canvas-container"></div>
    <div class="info">
        <div>ASIN: {asin}</div>
        <div>Drag to rotate | Scroll to zoom | Right-click to pan</div>
    </div>
    <div class="controls">
        <button onclick="resetCamera()">Reset View</button>
        <button onclick="toggleAutoRotate()">Auto Rotate</button>
        <button onclick="toggleWireframe()">Wireframe</button>
        <button onclick="captureScreenshot()">Screenshot</button>
    </div>

    <script type="importmap">
    {{
        "imports": {{
            "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
            "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
        }}
    }}
    </script>
    <script type="module">
        import * as THREE from 'three';
        import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';
        import {{ GLTFLoader }} from 'three/addons/loaders/GLTFLoader.js';

        let scene, camera, renderer, controls, model;
        let autoRotate = true;
        let wireframeMode = false;

        function init() {{
            // Scene
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x1a1a2e);

            // Camera
            camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(3, 2, 3);

            // Renderer
            renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.shadowMap.enabled = true;
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.toneMappingExposure = 1.2;
            document.getElementById('canvas-container').appendChild(renderer.domElement);

            // Controls
            controls = new OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            controls.autoRotate = autoRotate;
            controls.autoRotateSpeed = 2;

            // Lights
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
            scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
            directionalLight.position.set(5, 5, 5);
            directionalLight.castShadow = true;
            scene.add(directionalLight);

            const fillLight = new THREE.DirectionalLight(0x8888ff, 0.3);
            fillLight.position.set(-5, 3, -5);
            scene.add(fillLight);

            // Ground plane
            const groundGeometry = new THREE.PlaneGeometry(20, 20);
            const groundMaterial = new THREE.MeshStandardMaterial({{
                color: 0x222244, roughness: 0.8, metalness: 0.2
            }});
            const ground = new THREE.Mesh(groundGeometry, groundMaterial);
            ground.rotation.x = -Math.PI / 2;
            ground.position.y = -1;
            ground.receiveShadow = true;
            scene.add(ground);

            // Load model
            const loader = new GLTFLoader();
            loader.load('{model_filename}', (gltf) => {{
                model = gltf.scene;

                // Auto-center and scale
                const box = new THREE.Box3().setFromObject(model);
                const center = box.getCenter(new THREE.Vector3());
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 2 / maxDim;

                model.scale.setScalar(scale);
                model.position.sub(center.multiplyScalar(scale));

                model.traverse((child) => {{
                    if (child.isMesh) {{
                        child.castShadow = true;
                        child.receiveShadow = true;
                    }}
                }});

                scene.add(model);
                document.getElementById('loading').style.display = 'none';
            }},
            (progress) => {{
                const pct = Math.round((progress.loaded / progress.total) * 100);
                document.querySelector('.loading div:last-child').textContent =
                    `Loading 3D Model... ${{pct}}%`;
            }},
            (error) => {{
                console.error('Model load error:', error);
                document.querySelector('.loading div:last-child').textContent =
                    'Failed to load 3D model';
            }});

            window.addEventListener('resize', onResize);
            animate();
        }}

        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }}

        function onResize() {{
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }}

        // Global functions for buttons
        window.resetCamera = () => {{
            camera.position.set(3, 2, 3);
            controls.target.set(0, 0, 0);
            controls.update();
        }};

        window.toggleAutoRotate = () => {{
            autoRotate = !autoRotate;
            controls.autoRotate = autoRotate;
        }};

        window.toggleWireframe = () => {{
            wireframeMode = !wireframeMode;
            if (model) {{
                model.traverse((child) => {{
                    if (child.isMesh) {{
                        child.material.wireframe = wireframeMode;
                    }}
                }});
            }}
        }};

        window.captureScreenshot = () => {{
            renderer.render(scene, camera);
            const link = document.createElement('a');
            link.download = '{asin}_3d_screenshot.png';
            link.href = renderer.domElement.toDataURL('image/png');
            link.click();
        }};

        init();
    </script>
</body>
</html>"""

        with open(preview_path, "w", encoding="utf-8") as f:
            f.write(html)

        logger.info(f"[3D] 预览页面已生成: {preview_path}")
        return preview_path
