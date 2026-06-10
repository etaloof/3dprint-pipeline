import * as THREE from "three";
import { OrbitControls } from "three-stdlib";
import { STLLoader } from "three-stdlib";

export class Viewer3D {
  private container: HTMLElement;
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private controls: OrbitControls;
  private mesh: THREE.Mesh | null = null;
  private loader = new STLLoader();

  constructor(container: HTMLElement) {
    this.container = container;
    const { clientWidth: w, clientHeight: h } = container;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0f1419);

    this.camera = new THREE.PerspectiveCamera(45, w / Math.max(h, 1), 0.1, 2000);
    this.camera.position.set(120, 90, 120);

    this.renderer = new THREE.WebGLRenderer({ antialias: true });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setSize(w, h);
    container.appendChild(this.renderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;

    const ambient = new THREE.AmbientLight(0xffffff, 0.55);
    const key = new THREE.DirectionalLight(0xffffff, 0.85);
    key.position.set(80, 120, 60);
    const fill = new THREE.DirectionalLight(0x88aaff, 0.35);
    fill.position.set(-60, 40, -80);
    this.scene.add(ambient, key, fill);

    const grid = new THREE.GridHelper(200, 20, 0x2f3f56, 0x1a2332);
    grid.position.y = -0.01;
    this.scene.add(grid);

    window.addEventListener("resize", this.onResize);
    this.animate();
  }

  private onResize = () => {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.camera.aspect = w / Math.max(h, 1);
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h);
  };

  private animate = () => {
    requestAnimationFrame(this.animate);
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  };

  async loadStl(url: string): Promise<void> {
    const geometry = await this.loader.loadAsync(url);
    geometry.computeVertexNormals();
    geometry.center();

    if (this.mesh) {
      this.scene.remove(this.mesh);
      this.mesh.geometry.dispose();
      (this.mesh.material as THREE.Material).dispose();
    }

    const material = new THREE.MeshStandardMaterial({
      color: 0x6699cc,
      metalness: 0.15,
      roughness: 0.55,
    });
    this.mesh = new THREE.Mesh(geometry, material);
    this.scene.add(this.mesh);

    const box = new THREE.Box3().setFromObject(this.mesh);
    const size = box.getSize(new THREE.Vector3()).length();
    const center = box.getCenter(new THREE.Vector3());
    this.controls.target.copy(center);
    this.camera.position.copy(center).add(new THREE.Vector3(size * 0.8, size * 0.6, size * 0.8));
    this.controls.update();
  }

  clear(): void {
    if (this.mesh) {
      this.scene.remove(this.mesh);
      this.mesh.geometry.dispose();
      (this.mesh.material as THREE.Material).dispose();
      this.mesh = null;
    }
  }
}
