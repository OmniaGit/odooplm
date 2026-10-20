// Live update of a .glb model: the viewer asks the server, every few seconds,
// for the checksum of every web file it shows, and loads again what changed
// at a check-in.
//
// - a part that changed: its copies get the new file, where they are;
// - an assembly that changed (the document shown too): it is built again from
//   its new file, which brings the components added, drops the ones removed,
//   moves the ones moved and follows a new revision; the parts that did not
//   change come from the cache;
// - a component whose file is not there yet (the child reached the server
//   after its assembly): asked again for a while after each update.
//
// The viewer says when it may not update (a measure, a section, a markup on
// screen): the update waits for it. Before updating it resets what depends on
// the parts shown (explosion, hidden parts, selection); after, it rebuilds the
// tree and lays the user's colours on again.
import { assemblyNodes, exportSuffix, isAssembly, loadAssemblyComponents } from '../../src/js/cad3d_features.js';
import { evictGltfParts, loadGltfPart, loadGltfRoots, placeGltfPart, prepareGltfPart } from './loaders.js';

const POLL_SECONDS = 15;
// polls after an update during which the missing components are asked again
const MISSING_RETRIES = 8;

function downloadUrl(documentId, checksum) {
	return `/plm/download_treejs_model?document_id=${documentId}&v=${checksum}`;
}

/** The materials of a copy are its own (placeGltfPart clones them); its
 * geometry is shared with the other copies and goes with the cache. */
function disposeCopy(object) {
	object.traverse((child) => {
		if (!child.isMesh || !child.material) return;
		(Array.isArray(child.material) ? child.material : [child.material]).forEach((material) => material.dispose());
	});
}

/** A root of the document shown owns its geometry too. */
function disposeRoot(object) {
	object.traverse((child) => {
		if (!child.isMesh) return;
		if (child.geometry) child.geometry.dispose();
		(Array.isArray(child.material) ? child.material : [child.material]).forEach((material) => material?.dispose());
	});
}

export class LiveUpdate {
	/**
	 * odooCad: the OdooCAD of the page
	 * options: documentId, documentName and checksum of the document shown;
	 *   blocker() -> what keeps the view from updating ('' when nothing);
	 *   beforeUpdate(), afterUpdate(count); notify(text)
	 */
	constructor(odooCad, options) {
		this.odooCad = odooCad;
		this.documentId = String(options.documentId);
		this.documentName = options.documentName;
		this.checksum = options.checksum || '';
		this.blocker = options.blocker || (() => '');
		this.beforeUpdate = options.beforeUpdate || (() => { });
		this.afterUpdate = options.afterUpdate || (() => { });
		this.notify = options.notify || (() => { });
		this.retries = 0;
		this.busy = false;
		this.waitingSaid = false;
		this.timer = null;
	}

	start() {
		if (this.timer) return;
		this.timer = setInterval(() => this.tick(), POLL_SECONDS * 1000);
	}

	stop() {
		clearInterval(this.timer);
		this.timer = null;
	}

	/** Every object of the scene that came from a web file. */
	placed() {
		const out = [];
		for (const item of this.odooCad.items) {
			item.traverse((child) => { if (child.userData.plm_glb) out.push(child); });
		}
		return out;
	}

	/** The checksum the viewer holds of each web file it shows. */
	shown() {
		const out = new Map([[this.documentId, this.checksum]]);
		for (const object of this.placed()) {
			const glb = object.userData.plm_glb;
			if (!glb.root) out.set(String(glb.document_id), glb.checksum || '');
		}
		return out;
	}

	/** The assemblies in the scene with components that hold no part yet. */
	missing() {
		const out = [];
		for (const object of this.placed()) {
			if (!isAssembly(object)) continue;
			const nodes = assemblyNodes(object).filter((node) => {
				const info = node.userData.plm_component;
				return !info.modified && info.engineering_code
					&& info.engineering_revision !== null && info.engineering_revision !== undefined
					&& !node.userData.plm_pending
					&& !node.children.some((child) => child.userData.plm_glb);
			});
			if (nodes.length) out.push({ object, nodes });
		}
		return out;
	}

	async tick() {
		if (this.busy || document.visibilityState !== 'visible') return;
		this.busy = true;
		try {
			const shown = this.shown();
			const response = await fetch(`/plm/web3d_changes?ids=${[...shown.keys()].join(',')}`);
			// a server restarting or a session gone: try again at the next poll
			if (!response.ok) return;
			const answer = await response.json();
			const changed = [...shown.keys()].filter((id) => answer[id] && answer[id] !== shown.get(id));
			const arrived = changed.length ? [] : await this.arrivedMissing();
			if (!changed.length && !arrived.length) return;
			const blocker = this.blocker();
			if (blocker) {
				if (!this.waitingSaid) this.notify(`The model changed on the server: it updates when ${blocker}`);
				this.waitingSaid = true;
				return;
			}
			this.waitingSaid = false;
			this.beforeUpdate();
			let count = 0;
			if (changed.length) {
				count += await this.apply(new Set(changed), answer);
				this.retries = MISSING_RETRIES;
			}
			count += await this.fillMissing();
			evictGltfParts(new Set(this.placed().map((object) => object.userData.plm_glb.url).filter(Boolean)));
			this.afterUpdate(count);
		} catch (error) {
			console.warn('live update failed', error);
		} finally {
			this.busy = false;
		}
	}

	/** The missing components whose file is on the server now: asked for a
	 * few polls after an update only, a part with no web file stays missing. */
	async arrivedMissing() {
		if (this.retries <= 0) return [];
		this.retries--;
		const arrived = [];
		for (const { object, nodes } of this.missing()) {
			const glb = object.userData.plm_glb;
			const info = nodes[0].userData.plm_component;
			const query = new URLSearchParams({
				engineering_code: info.engineering_code,
				engineering_revision: info.engineering_revision,
				suffix: exportSuffix(glb.name),
			});
			if (info.glb) query.set('name', info.glb);
			query.set('parent_id', glb.document_id);
			const found = await fetch(`/plm/web3d_component?${query}`).then((r) => r.json()).catch(() => ({}));
			if (found && found.url) arrived.push(object);
		}
		return arrived;
	}

	/** Load again what changed; the number of files loaded again. */
	async apply(changed, answer) {
		if (changed.has(this.documentId)) {
			// the document shown: all of it again, the unchanged parts from the cache
			await this.reloadRoot(answer[this.documentId]);
			return changed.size;
		}
		const copies = this.placed().filter((object) => !object.userData.plm_glb.root
			&& changed.has(String(object.userData.plm_glb.document_id)));
		// an assembly built again brings its own parts as they are now
		const outer = copies.filter((object) => {
			for (let parent = object.parent; parent; parent = parent.parent) {
				if (copies.includes(parent)) return false;
			}
			return true;
		});
		for (const old of outer) {
			const glb = old.userData.plm_glb;
			const checksum = answer[String(glb.document_id)];
			const found = { document_id: glb.document_id, name: glb.name, checksum, url: downloadUrl(glb.document_id, checksum) };
			const part = await loadGltfPart(found.url);
			const node = old.parent;
			node.remove(old);
			disposeCopy(old);
			const copy = part.clone();
			node.add(copy);
			await placeGltfPart(copy, found);
		}
		return new Set(outer.map((object) => object.userData.plm_glb.document_id)).size;
	}

	async reloadRoot(checksum) {
		const roots = await loadGltfRoots(downloadUrl(this.documentId, checksum));
		for (const old of this.odooCad.items.filter((item) => item.userData.plm_glb?.root)) {
			this.odooCad.removeItemToSeen(old);
			disposeRoot(old);
		}
		const assemblies = [];
		for (const root of roots) {
			root.userData.plm_glb = { document_id: this.documentId, name: this.documentName, root: true };
			this.odooCad.addItemToScene(root, true, true, false);
			prepareGltfPart(root);
			if (isAssembly(root)) assemblies.push(root);
		}
		this.checksum = checksum;
		await Promise.all(assemblies.map((assembly) => loadAssemblyComponents(
			assembly, this.documentName, placeGltfPart, loadGltfPart, this.documentId)));
	}

	/** Fill the components with no part that can be filled; how many were. */
	async fillMissing() {
		const before = this.missing().reduce((sum, { nodes }) => sum + nodes.length, 0);
		for (const { object } of this.missing()) {
			const glb = object.userData.plm_glb;
			await loadAssemblyComponents(object, glb.name, placeGltfPart, loadGltfPart, glb.document_id);
		}
		const after = this.missing().reduce((sum, { nodes }) => sum + nodes.length, 0);
		return Math.max(0, before - after);
	}
}
