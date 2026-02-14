import { useEffect, useRef, useState } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import URDFLoader from 'urdf-loader';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';

interface RobotModelProps {
  position?: [number, number, number];
  rotation?: [number, number, number];
  urdfPath: string;
  meshPath?: string;
  jointAngles?: { [key: string]: number };
}

export default function RobotModel({
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  urdfPath,
  meshPath = '',
  jointAngles = {},
}: RobotModelProps) {
  const { scene } = useThree();
  const robotRef = useRef<any>(null);       // The actual URDF robot (for setJointValue)
  const wrapperRef = useRef<THREE.Group | null>(null); // The outer group (for position/rotation)
  const [isLoaded, setIsLoaded] = useState(false);

  // Use refs for position/rotation to prevent URDF reload when these change.
  // The load effect only depends on [scene, urdfPath, meshPath].
  const positionRef = useRef(position);
  const rotationRef = useRef(rotation);
  positionRef.current = position;
  rotationRef.current = rotation;

  useEffect(() => {
    console.log('RobotModel: Starting load...', { urdfPath, meshPath });

    const manager = new THREE.LoadingManager();

    manager.onLoad = () => {
      console.log('RobotModel: All resources loaded');
    };

    manager.onError = (url) => {
      console.error('RobotModel: Error loading:', url);
    };

    const loader = new URDFLoader(manager);

    // Set working path for relative mesh resolution
    loader.workingPath = meshPath;

    // Custom mesh loader to handle STL files
    loader.loadMeshCb = (path: string, manager: THREE.LoadingManager, onComplete: (mesh: THREE.Object3D, err?: Error) => void) => {
      // The URDF uses relative paths like "meshes/irb6700/visual/base_link.stl"
      // We need to prepend our meshPath
      let resolvedPath = path;

      if (path.startsWith('meshes/')) {
        resolvedPath = meshPath + path;
      }

      const stlLoader = new STLLoader(manager);
      stlLoader.load(
        resolvedPath,
        (geometry) => {
          const material = new THREE.MeshStandardMaterial({
            color: 0xf0f0f0,
            metalness: 0.3,
            roughness: 0.6,
          });
          const mesh = new THREE.Mesh(geometry, material);
          onComplete(mesh);
        },
        undefined,
        (err) => {
          console.error('RobotModel: Error loading mesh:', resolvedPath, err);
          const emptyMesh = new THREE.Object3D();
          onComplete(emptyMesh, err as Error);
        }
      );
    };

    // Load the URDF
    loader.load(
      urdfPath,
      (robot) => {
        console.log('RobotModel: URDF loaded successfully');

        // Remove previous wrapper if it exists
        if (wrapperRef.current) {
          scene.remove(wrapperRef.current);
        }

        // Create wrapper group for position/rotation
        // Read from refs so we get the latest values without retriggering load
        const wrapper = new THREE.Group();
        wrapper.position.set(...positionRef.current);
        wrapper.rotation.set(...rotationRef.current);
        wrapper.add(robot);

        // Add to scene via wrapper
        scene.add(wrapper);
        wrapperRef.current = wrapper;
        robotRef.current = robot;
        setIsLoaded(true);

        console.log('RobotModel: Added to scene at position:', positionRef.current);
      },
      undefined,
      (err) => {
        console.error('RobotModel: Error loading URDF:', err);
      }
    );

    // Cleanup on unmount
    return () => {
      if (wrapperRef.current) {
        scene.remove(wrapperRef.current);
      }
    };
  }, [scene, urdfPath, meshPath]); // Only reload URDF when these change

  // Update joint angles every render frame using useFrame.
  // This is more reliable than useEffect during animation playback because
  // React may batch state updates, but useFrame runs every requestAnimationFrame.
  const jointAnglesRef = useRef(jointAngles);
  jointAnglesRef.current = jointAngles;
  const prevAnglesRef = useRef<Record<string, number>>({});

  useFrame(() => {
    if (!robotRef.current || !isLoaded) return;
    const angles = jointAnglesRef.current;

    // Dirty check: only update joints if any angle changed
    let changed = false;
    for (const [name, val] of Object.entries(angles)) {
      if (prevAnglesRef.current[name] !== val) {
        changed = true;
        break;
      }
    }
    if (!changed) return;

    for (const [name, val] of Object.entries(angles)) {
      try {
        robotRef.current.setJointValue(name, val);
      } catch (_e) {
        // Joint may not exist — ignore silently
      }
    }
    prevAnglesRef.current = { ...angles };
  });

  // Update position and rotation on the wrapper (without reloading the robot)
  useEffect(() => {
    if (wrapperRef.current && isLoaded) {
      wrapperRef.current.position.set(...position);
      wrapperRef.current.rotation.set(...rotation);
    }
  }, [position[0], position[1], position[2], rotation[0], rotation[1], rotation[2], isLoaded]);

  // This component doesn't render anything directly - it manages Three.js objects
  return null;
}
