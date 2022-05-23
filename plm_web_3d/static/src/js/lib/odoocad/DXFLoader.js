import * as THREE from '../three.js/build/three.module.js';
import {DxfWorker} from "../dxf-viewer/src/DxfWorker.js"
import {BatchingKey} from "../dxf-viewer/src/BatchingKey.js"

class Batch {
    /**
     * @param viewer {DxfViewer}
     * @param scene Serialized scene.
     * @param batch Serialized scene batch.
     */
    constructor(viewer, scene, batch) {
        this.viewer = viewer
        this.key = batch.key

        if (batch.hasOwnProperty("verticesOffset")) {
            const verticesArray =
                new Float32Array(scene.vertices,
                                 batch.verticesOffset * Float32Array.BYTES_PER_ELEMENT,
                                 batch.verticesSize)
            if (this.key.geometryType !== BatchingKey.GeometryType.POINT_INSTANCE ||
                scene.pointShapeHasDot) {
                this.vertices = new THREE.BufferAttribute(verticesArray, 2)
            }
            if (this.key.geometryType === BatchingKey.GeometryType.POINT_INSTANCE) {
                this.transforms = new THREE.InstancedBufferAttribute(verticesArray, 2)
            }
        }

        if (batch.hasOwnProperty("chunks")) {
            this.chunks = []
            for (const rawChunk of batch.chunks) {

                const verticesArray =
                    new Float32Array(scene.vertices,
                                     rawChunk.verticesOffset * Float32Array.BYTES_PER_ELEMENT,
                                     rawChunk.verticesSize)
                const indicesArray =
                    new Uint16Array(scene.indices,
                                    rawChunk.indicesOffset * Uint16Array.BYTES_PER_ELEMENT,
                                    rawChunk.indicesSize)
                this.chunks.push({
                    vertices: new THREE.BufferAttribute(verticesArray, 2),
                    indices: new THREE.BufferAttribute(indicesArray, 1)
                })
            }
        }

        if (batch.hasOwnProperty("transformsOffset")) {
            const transformsArray =
                new Float32Array(scene.transforms,
                                 batch.transformsOffset * Float32Array.BYTES_PER_ELEMENT,
                                 batch.transformsSize)
            /* Each transform is 3x2 matrix which is split into two 3D vectors which will occupy two
             * attribute slots.
             */
            const buf = new THREE.InstancedInterleavedBuffer(transformsArray, 6)
            this.transforms0 = new THREE.InterleavedBufferAttribute(buf, 3, 0)
            this.transforms1 = new THREE.InterleavedBufferAttribute(buf, 3, 3)
        }

        if (this.key.geometryType === BatchingKey.GeometryType.BLOCK_INSTANCE ||
            this.key.geometryType === BatchingKey.GeometryType.POINT_INSTANCE) {

            const layer = this.viewer.layers.get(this.key.layerName)
            if (layer) {
                this.layerColor = layer.color
            } else {
                this.layerColor = 0
            }
        }
    }

    GetInstanceType() {
        switch (this.key.geometryType) {
        case BatchingKey.GeometryType.BLOCK_INSTANCE:
            return InstanceType.FULL
        case BatchingKey.GeometryType.POINT_INSTANCE:
            return InstanceType.POINT
        default:
            return InstanceType.NONE
        }
    }

    /** Create scene objects corresponding to batch data.
     * @param instanceBatch {?Batch} Batch with instance transform. Null for non-instanced object.
     */
    *CreateObjects(instanceBatch = null) {
        if (this.key.geometryType === BatchingKey.GeometryType.BLOCK_INSTANCE ||
            this.key.geometryType === BatchingKey.GeometryType.POINT_INSTANCE) {

            if (instanceBatch !== null) {
                throw new Error("Unexpected instance batch specified for instance batch")
            }
            yield* this._CreateBlockInstanceObjects()
            return
        }
        yield* this._CreateObjects(instanceBatch)
    }

    *_CreateObjects(instanceBatch) {
        const color = instanceBatch ?
            instanceBatch._GetInstanceColor(this.key.color) : this.key.color

        //XXX line type
        const materialFactory =
            this.key.geometryType === BatchingKey.GeometryType.POINTS ||
            this.key.geometryType === BatchingKey.GeometryType.POINT_INSTANCE ?
                this.viewer._GetSimplePointMaterial : this.viewer._GetSimpleColorMaterial

        const material = new THREE.MeshPhongMaterial();
        material.color.setHSL(0, 1, .5);  // red
        material.flatShading = true; 
        
        //materialFactory.call(this.viewer, this.viewer._TransformColor(color),
        //                                      instanceBatch?.GetInstanceType() ?? InstanceType.NONE)

        let objConstructor
        switch (this.key.geometryType) {
        case BatchingKey.GeometryType.POINTS:
        /* This method also called for creating dots for shaped point instances. */
        case BatchingKey.GeometryType.POINT_INSTANCE:
            objConstructor = THREE.Points
            break
        case BatchingKey.GeometryType.LINES:
        case BatchingKey.GeometryType.INDEXED_LINES:
            objConstructor = THREE.LineSegments
            break
        case BatchingKey.GeometryType.TRIANGLES:
        case BatchingKey.GeometryType.INDEXED_TRIANGLES:
            objConstructor = THREE.Mesh
            break
        default:
            throw new Error("Unexpected geometry type:" + this.key.geometryType)
        }
        function pairs(arr) {
            var res = new Float32Array(arr.length/2*3);
            var l = arr.length;
            var ind=0;
            for(var i=0; i<l; i=i+2){
                res[ind] = arr[i];
                res[ind+1] = arr[i+1];
                res[ind+2] = 0.0;
                ind=ind+3;                
            }
            return res;
        }

        function CreateObject(vertices, indices) {
            const geometry = instanceBatch ?
                new THREE.InstancedBufferGeometry() : new THREE.BufferGeometry()
            const array=pairs(vertices.array);
            geometry.setAttribute("position", new THREE.BufferAttribute(array,3))
            instanceBatch?._SetInstanceTransformAttribute(geometry)
            if (indices) {
                geometry.setIndex(indices)
            }
            const obj = new objConstructor(geometry, material)
            obj.frustumCulled = false
            obj.matrixAutoUpdate = false
            return obj
        }

        if (this.chunks) {
            for (const chunk of this.chunks) {
                yield CreateObject(chunk.vertices, chunk.indices)
            }
        } else {
            yield CreateObject(this.vertices)
        }
    }

    /**
     * @param geometry {InstancedBufferGeometry}
     */
    _SetInstanceTransformAttribute(geometry) {
        if (!geometry.isInstancedBufferGeometry) {
            throw new Error("InstancedBufferGeometry expected")
        }
        if (this.key.geometryType === BatchingKey.GeometryType.POINT_INSTANCE) {
            geometry.setAttribute("instanceTransform", this.transforms)
        } else {
            geometry.setAttribute("instanceTransform0", this.transforms0)
            geometry.setAttribute("instanceTransform1", this.transforms1)
        }
    }

    *_CreateBlockInstanceObjects() {
        const block = this.viewer.blocks.get(this.key.blockName)
        if (!block) {
            return
        }
        for (const batch of block.batches) {
            yield* batch.CreateObjects(this)
        }
        if (this.hasOwnProperty("vertices")) {
            /* Dots for point shapes. */
            yield* this._CreateObjects()
        }
    }

    /**
     * @param defColor {number} Color value for block definition batch.
     * @return {number} RGB color value for a block instance.
     */
    _GetInstanceColor(defColor) {
        return defColor;
        if (defColor === ColorCode.BY_BLOCK) {
            return this.key.color
        } else if (defColor === ColorCode.BY_LAYER) {
            return this.layerColor
        } else {
            return defColor
        }
    }
}

class Layer {
    constructor(name, color) {
        this.name = name
        this.color = color
        this.objects = []
    }

    PushObject(obj) {
        this.objects.push(obj)
    }

    Dispose() {
        for (const obj of this.objects) {
            obj.geometry.dispose()
        }
        this.objects = null
    }
}

class Block {
    constructor() {
        this.batches = []
    }

    /** @param batch {Batch} */
    PushBatch(batch) {
        this.batches.push(batch)
    }
}

class DXFLoader extends THREE.Loader {

		constructor( manager ) {
			super( manager );
			this.layers = new Map()
            /* Indexed by block name, value is Block instance. */
            this.blocks = new Map()
		}

		async load( url, onLoad, onProgress, onError ) {

			const scope = this;
			/*
			const loader = new THREE.FileLoader( this.manager );
			loader.setPath( this.path );
			loader.setRequestHeader( this.requestHeader );
			loader.setWithCredentials( this.withCredentials );
			loader.load( url, function ( text ) {
*/
				try {
                    //
                    this.worker = new DxfWorker(null);
                    const scene = await this.worker.Load(url, null, this.options, onProgress);
                    await this.worker.Destroy();
                    this.worker = null;
                    //
                    this.origin = scene.origin;
                    this.bounds = scene.bounds;
                    this.hasMissingChars = scene.hasMissingChars;
                    //
                    for (const layer of scene.layers) {
                        this.layers.set(layer.name, new Layer(layer.name, layer.color));
                    }

                    /* Load all blocks on the first pass. */
                    for (const batch of scene.batches) {
                        if (batch.key.blockName !== null &&
                            batch.key.geometryType !== BatchingKey.GeometryType.BLOCK_INSTANCE &&
                            batch.key.geometryType !== BatchingKey.GeometryType.POINT_INSTANCE) {
            
                            let block = this.blocks.get(batch.key.blockName);
                            if (!block) {
                                block = new Block();
                                this.blocks.set(batch.key.blockName, block);
                            }
                            block.PushBatch(new Batch(this, scene, batch));
                        }
                    }

                    console.log(`DXF scene:
                     ${scene.batches.length} batches,
                     ${this.layers.size} layers,
                     ${this.blocks.size} blocks,
                     vertices ${scene.vertices.byteLength} B,
                     indices ${scene.indices.byteLength} B
                     transforms ${scene.transforms.byteLength} B`)
                    const objects = [];
                    /* Instantiate all entities. */
                    for (const batch of scene.batches) {
                        for (const obj of this._GetObjectBatch(scene, batch)){
                            objects.push(obj);
                            }
                    }
                    //this._Emit("loaded")
				    onLoad(objects);
				    
				} catch ( e ) {

					if ( onError ) {

						onError( e );

					} else {

						console.error( e );

					}

					scope.manager.itemError( url );

				}

			//}, onProgress, onError );

		}

        _GetObjectBatch(scene, batch) {
            if (batch.key.blockName !== null &&
                batch.key.geometryType !== BatchingKey.GeometryType.BLOCK_INSTANCE &&
                batch.key.geometryType !== BatchingKey.GeometryType.POINT_INSTANCE) {
                /* Block definition. */
                return []
            }
            return new Batch(this, scene, batch).CreateObjects()
        }
        
		setMaterials( materials ) {

			this.materials = materials;
			return this;

		}
}

export { DXFLoader };
