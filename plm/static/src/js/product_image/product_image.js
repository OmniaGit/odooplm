/** @odoo-module */
import {Component, onWillUpdateProps, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";

// One read per product and per kind of component for the whole page: list
// rows render again on every edit, and the same product is often on many rows
const infoCache = new Map();

/**
 * Image of a product (product.product or product.template) that opens its
 * linked documents on click, with the zoom of the image on hover; a folder
 * icon when the product has no image.
 * Used by the many2one widgets that show a product (plm_many2one_image and
 * the widgets of other modules), so the link to the documents is written once.
 * A module extends it by overriding fetchInfo (what is read for the product)
 * and onClick, with a template that inherits plm.PlmProductImage.
 */
export class PlmProductImage extends Component {
    static template = "plm.PlmProductImage";
    static props = {
        resModel: String,
        resId: {type: [Number, Boolean], optional: true},
        // the image shown by the zoom; the thumbnail is always image_128
        imageField: {type: String, optional: true},
        linkedField: {type: String, optional: true},
    };
    static defaultProps = {
        resId: false,
        imageField: "image_1920",
        linkedField: "linkeddocuments",
    };
    // the cache key of what fetchInfo reads
    static infoKind = "image";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({info: {}});
        this.loadInfo(this.props);
        onWillUpdateProps((nextProps) => {
            if (
                nextProps.resModel !== this.props.resModel ||
                nextProps.resId !== this.props.resId
            ) {
                this.loadInfo(nextProps);
            }
        });
    }

    /**
     * What the component shows for the product: {unique} is the write date
     * of the product when it has an image, false otherwise.
     */
    async fetchInfo(props) {
        // bin_size: only the size of the image is read, never its data
        const [record] = await this.orm.read(
            props.resModel,
            [props.resId],
            ["image_128", "write_date"],
            {context: {bin_size: true}}
        );
        return {unique: record && record.image_128 ? record.write_date : false};
    }

    async loadInfo(props) {
        this.state.info = {};
        if (!props.resId) {
            return;
        }
        const key = `${this.constructor.infoKind},${props.resModel},${props.resId}`;
        if (!infoCache.has(key)) {
            infoCache.set(
                key,
                this.fetchInfo(props).catch(() => {
                    infoCache.delete(key);
                    return {};
                })
            );
        }
        const info = await infoCache.get(key);
        if (props.resModel === this.props.resModel && props.resId === this.props.resId) {
            this.state.info = info;
        }
    }

    imageUrl(fieldName) {
        const unique = encodeURIComponent(this.state.info.unique);
        return `/web/image/${this.props.resModel}/${this.props.resId}/${fieldName}?unique=${unique}`;
    }

    get thumbnailUrl() {
        return this.imageUrl("image_128");
    }

    get tooltipInfo() {
        return JSON.stringify({url: this.imageUrl(this.props.imageField)});
    }

    async onClick(ev) {
        // the image can sit inside a link or a row that opens something else
        ev.preventDefault();
        ev.stopPropagation();
        if (!this.props.resId) {
            return;
        }
        const action = await this.orm.call(
            this.props.resModel,
            "action_open_linked_field",
            [[this.props.resId], this.props.linkedField]
        );
        return this.action.doAction(action);
    }
}
