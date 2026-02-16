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
  /** TCP offset [x, y, z, rx, ry, rz] in meters/degrees — from endEffector config */
  tcpOffset?: [number, number, number, number, number, number];
  /** Whether to show the TCP visualization frame */
  showTCP?: boolean;
}

export default function RobotModel({
  position = [0, 0, 0],
  rotation = [0, 0, 0],
  urdfPath,
  meshPath = '',
  jointAngles = {},
  tcpOffset = [0, 0, 0.15, 0, 0, 0],
  showTCP = true,
}: RobotModelProps) {
  const { scene } = useThree();
  const robotRef = useRef<any>(null);       // The actual URDF robot (for setJointValue)
  const wrapperRef = useRef<THREE.Group | null>(null); // The outer group (for position/rotation)
  const tcpMarkerRef = useRef<THREE.Group | null>(null); // TCP visualization group
  const [isLoaded, setIsLoaded] = useState(false);

  // Use refs for position/rotation to prevent URDF reload when these change.
  // The load effect only depends on [scene, urdfPath, meshPath].
  const positionRef = useRef(position);
  const rotationRef = useRef(rotation);
  positionRef.current = position;
  rotationRef.current = rotation;

  useEffect(() => {

    const manager = new THREE.LoadingManager();

    manager.onLoad = () => {
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

        // Create TCP visualization marker (sphere + axes)
        const tcpGroup = new THREE.Group();
        tcpGroup.name = 'tcp-marker';

        // Small orange sphere at TCP
        const sphereGeom = new THREE.SphereGeometry(0.012, 16, 16);
        const sphereMat = new THREE.MeshBasicMaterial({
          color: 0xff6600,
          transparent: true,
          opacity: 0.9,
          depthTest: false,
        });
        const sphere = new THREE.Mesh(sphereGeom, sphereMat);
        sphere.renderOrder = 999;
        tcpGroup.add(sphere);

        // XYZ axes helper at TCP
        const axes = new THREE.AxesHelper(0.06);
        axes.renderOrder = 999;
        (axes.material as THREE.Material).depthTest = false;
        tcpGroup.add(axes);

        scene.add(tcpGroup);
        tcpMarkerRef.current = tcpGroup;

        setIsLoaded(true);
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
      if (tcpMarkerRef.current) {
        scene.remove(tcpMarkerRef.current);
      }
    };
  }, [scene, urdfPath, meshPath]); // Only reload URDF when these change

  // Update joint angles every render frame using useFrame.
  // This is more reliable than useEffect during animation playback because
  // React may batch state updates, but useFrame runs every requestAnimationFrame.
  const jointAnglesRef = useRef(jointAngles);
  jointAnglesRef.current = jointAngles;
  const prevAnglesRef = useRef<Record<string, number>>({});

  // Keep refs to TCP offset and showTCP for useFrame access
  const tcpOffsetRef = useRef(tcpOffset);
  tcpOffsetRef.current = tcpOffset;
  const showTCPRef = useRef(showTCP);
  showTCPRef.current = showTCP;

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

    if (changed) {
      for (const [name, val] of Object.entries(angles)) {
        try {
          robotRef.current.setJointValue(name, val);
        } catch (_e) {
          // Joint may not exist — ignore silently
        }
      }
      prevAnglesRef.current = { ...angles };
    }

    // Update TCP marker position — find the last link's world position
    if (tcpMarkerRef.current && showTCPRef.current) {
      tcpMarkerRef.current.visible = true;
      try {
        // Find the end-effector link (last joint's child link)
        const robot = robotRef.current;

        // Use the known kinematic chain order for ABB robots: joint_6 is
        // always the last joint.  Fallback: iterate all joint names sorted
        // and pick the last one so the code works for non-ABB URDFs too.
        let lastLink: THREE.Object3D | null = null;
        const joints = robot.joints || {};

        // Try known last joint names first (ABB, KUKA, UR conventions)
        const knownLastJoints = ['joint_6', 'joint6', 'J6', 'wrist_3_joint'];
        for (const name of knownLastJoints) {
          if (joints[name]) {
            lastLink = joints[name].children?.[0] || joints[name];
            break;
          }
        }

        // Fallback: sort joint names naturally and use the last
        if (!lastLink) {
          const jointNames = Object.keys(joints).sort();
          if (jointNames.length > 0) {
            const lastJointName = jointNames[jointNames.length - 1];
            const lastJoint = joints[lastJointName];
            if (lastJoint) {
              lastLink = lastJoint.children?.[0] || lastJoint;
            }
          }
        }

        if (lastLink) {
          // Get world position of the last link
          const worldPos = new THREE.Vector3();
          lastLink.getWorldPosition(worldPos);

          // Apply TCP offset in the link's local frame
          const offset = tcpOffsetRef.current;
          const localOffset = new THREE.Vector3(offset[0], offset[1], offset[2]);

          // Get the link's world quaternion to transform the offset
          const worldQuat = new THREE.Quaternion();
          lastLink.getWorldQuaternion(worldQuat);
          localOffset.applyQuaternion(worldQuat);

          tcpMarkerRef.current.position.copy(worldPos).add(localOffset);

          // Apply TCP orientation
          tcpMarkerRef.current.quaternion.copy(worldQuat);
        }
      } catch (_e) {
        // If anything fails, hide the marker
        tcpMarkerRef.current.visible = false;
      }
    } else if (tcpMarkerRef.current) {
      tcpMarkerRef.current.visible = false;
    }
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
