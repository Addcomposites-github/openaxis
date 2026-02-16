/**
 * geometryDB.ts — IndexedDB-backed persistent geometry file storage.
 *
 * Stores raw geometry file data (ArrayBuffer) alongside part metadata so that
 * imported geometry survives page reloads, HMR, and session boundaries.
 *
 * Schema:
 *   Database:  "openaxis-geometry"
 *   Store:     "files"
 *   Key:       partId (string)
 *   Value:     { partId, fileName, fileType, data: ArrayBuffer, storedAt: number }
 */

const DB_NAME = 'openaxis-geometry';
const DB_VERSION = 1;
const STORE_NAME = 'files';

export interface StoredGeometryFile {
  partId: string;
  fileName: string;
  fileType: string; // MIME type or extension
  data: ArrayBuffer;
  storedAt: number; // timestamp
}

// ─── Database connection ────────────────────────────────────────────────────

let _dbPromise: Promise<IDBDatabase> | null = null;

function openDB(): Promise<IDBDatabase> {
  if (_dbPromise) return _dbPromise;

  _dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: 'partId' });
      }
    };

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => {
      console.error('[GeometryDB] Failed to open database:', request.error);
      _dbPromise = null;
      reject(request.error);
    };
  });

  return _dbPromise;
}

// ─── Public API ─────────────────────────────────────────────────────────────

/**
 * Save a geometry file to IndexedDB.
 * Converts the File to an ArrayBuffer for persistent storage.
 */
export async function saveGeometryFile(partId: string, file: File): Promise<void> {
  try {
    const db = await openDB();
    const data = await file.arrayBuffer();

    const record: StoredGeometryFile = {
      partId,
      fileName: file.name,
      fileType: file.type || file.name.split('.').pop() || 'stl',
      data,
      storedAt: Date.now(),
    };

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const request = store.put(record);
      request.onsuccess = () => resolve();
      request.onerror = () => {
        console.error('[GeometryDB] Failed to save file:', request.error);
        reject(request.error);
      };
    });
  } catch (e) {
    console.error('[GeometryDB] saveGeometryFile error:', e);
  }
}

/**
 * Load a geometry file from IndexedDB.
 * Returns a File object reconstructed from the stored ArrayBuffer,
 * or undefined if not found.
 */
export async function loadGeometryFile(partId: string): Promise<File | undefined> {
  try {
    const db = await openDB();

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const request = store.get(partId);

      request.onsuccess = () => {
        const record = request.result as StoredGeometryFile | undefined;
        if (!record) {
          resolve(undefined);
          return;
        }
        // Reconstruct a File object from the stored ArrayBuffer
        const blob = new Blob([record.data], { type: record.fileType });
        const file = new File([blob], record.fileName, { type: record.fileType });
        resolve(file);
      };

      request.onerror = () => {
        console.error('[GeometryDB] Failed to load file:', request.error);
        reject(request.error);
      };
    });
  } catch (e) {
    console.error('[GeometryDB] loadGeometryFile error:', e);
    return undefined;
  }
}

/**
 * Delete a geometry file from IndexedDB.
 */
export async function deleteGeometryFile(partId: string): Promise<void> {
  try {
    const db = await openDB();

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const request = store.delete(partId);
      request.onsuccess = () => resolve();
      request.onerror = () => {
        console.error('[GeometryDB] Failed to delete file:', request.error);
        reject(request.error);
      };
    });
  } catch (e) {
    console.error('[GeometryDB] deleteGeometryFile error:', e);
  }
}

/**
 * Load ALL geometry files from IndexedDB.
 * Returns a Map of partId → File for bulk restoration.
 */
export async function loadAllGeometryFiles(): Promise<Map<string, File>> {
  const result = new Map<string, File>();

  try {
    const db = await openDB();

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const request = store.getAll();

      request.onsuccess = () => {
        const records = request.result as StoredGeometryFile[];
        for (const record of records) {
          const blob = new Blob([record.data], { type: record.fileType });
          const file = new File([blob], record.fileName, { type: record.fileType });
          result.set(record.partId, file);
        }
        console.log(`[GeometryDB] Restored ${result.size} geometry files from IndexedDB`);
        resolve(result);
      };

      request.onerror = () => {
        console.error('[GeometryDB] Failed to load all files:', request.error);
        reject(request.error);
      };
    });
  } catch (e) {
    console.error('[GeometryDB] loadAllGeometryFiles error:', e);
    return result;
  }
}

/**
 * List all part IDs that have stored geometry.
 */
export async function listStoredPartIds(): Promise<string[]> {
  try {
    const db = await openDB();

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const request = store.getAllKeys();

      request.onsuccess = () => resolve(request.result as string[]);
      request.onerror = () => {
        console.error('[GeometryDB] Failed to list keys:', request.error);
        reject(request.error);
      };
    });
  } catch (e) {
    console.error('[GeometryDB] listStoredPartIds error:', e);
    return [];
  }
}

/**
 * Clear all geometry files from IndexedDB.
 */
export async function clearAllGeometryFiles(): Promise<void> {
  try {
    const db = await openDB();

    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      const store = tx.objectStore(STORE_NAME);
      const request = store.clear();
      request.onsuccess = () => resolve();
      request.onerror = () => {
        console.error('[GeometryDB] Failed to clear store:', request.error);
        reject(request.error);
      };
    });
  } catch (e) {
    console.error('[GeometryDB] clearAllGeometryFiles error:', e);
  }
}
