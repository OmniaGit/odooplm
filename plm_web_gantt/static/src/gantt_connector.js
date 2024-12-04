import { Component, onWillRender, useEffect, useRef } from "@odoo/owl";

export function getStrokeAndHoveredStrokeColor(r, g, b) {
    return {
        color: `rgba(${r},${g},${b},0.5)`,
        highlightedColor: `rgba(${r},${g},${b},1)`,
    };
}

export const COLORS = {
    default: getStrokeAndHoveredStrokeColor(143, 143, 143),
    error: getStrokeAndHoveredStrokeColor(211, 65, 59),
    warning: getStrokeAndHoveredStrokeColor(236, 151, 31),
    outline: getStrokeAndHoveredStrokeColor(255, 255, 255),
};

/** @extends {Component<{ reactive: ConnectorProps }, any>} */
export class GanttConnector extends Component {
    static props = {
        reactive: {
            type: Object,
            shape: {
                id: String,
                alert: {
                    type: [{ value: "error" }, { value: "warning" }, { value: null }],
                    optional: true,
                },
                highlighted: { type: Boolean, optional: true },
                displayButtons: { type: Boolean, optional: true },
                sourcePoint: [
                    { value: null },
                    Function,
                    { type: Object, shape: { left: Number, top: Number } },
                ],
                targetPoint: [
                    { value: null },
                    Function,
                    { type: Object, shape: { left: Number, top: Number } },
                ],
            },
        },
        onLeftButtonClick: { type: Function, optional: true },
        onRemoveButtonClick: { type: Function, optional: true },
        onRightButtonClick: { type: Function, optional: true },
    };
    static defaultProps = {
        highlighted: false,
        displayButtons: false,
    };
    static template = "plm_web_gantt.GanttConnector";

    rootRef = useRef("root");
    style = {
        hoverEaseWidth: 10,
        slackness: 0.9,
        stroke: { width: 2 },
        outlineStroke: { width: 1 },
    };

    get alert() {
        return this.props.reactive.alert;
    }

    get displayButtons() {
        return this.props.reactive.displayButtons;
    }

    get highlighted() {
        return this.props.reactive.highlighted;
    }

    get id() {
        return this.props.reactive.id;
    }

    get isNew() {
        return this.id.endsWith("new");
    }

    get sourcePoint() {
        return this.props.reactive.sourcePoint;
    }

    get targetPoint() {
        return this.props.reactive.targetPoint;
    }

    setup() {
        onWillRender(this.onWillRender);

        useEffect(
            (el, sourceLeft, sourceTop, targetLeft, targetTop) => {
                if (!el) {
                    return;
                }
                const { sourceControlPoint, targetControlPoint, removeButtonPosition } =
                    this.getPathInfo(
                        { left: sourceLeft, top: sourceTop },
                        { left: targetLeft, top: targetTop },
                        this.style.slackness
                    );

                const drawingCommands = [
                    `M`,
                    `${sourceLeft},${sourceTop}`,
                    `C`,
                    `${sourceControlPoint.left},${sourceControlPoint.top}`,
                    `${targetControlPoint.left},${targetControlPoint.top}`,
                    `${targetLeft},${targetTop}`,
                ].join(" ");

                const paths = el.querySelectorAll(
                    ".o_connector_stroke, .o_connector_stroke_hover_ease"
                );
                for (const path of paths) {
                    path.setAttribute("d", drawingCommands);
                }

                const svgButtons = el.querySelector(".o_connector_stroke_buttons");
                if (svgButtons) {
                    svgButtons.setAttribute("x", removeButtonPosition.left - 24);
                    svgButtons.setAttribute("y", removeButtonPosition.top - 8);
                }
            },
            () => this.getEffectDependencies()
        );
    }

    computeStyle({ alert, highlighted }) {
        const key = highlighted ? "highlightedColor" : "color";
        const strokeType = alert || "default";
        this.style = {
            hoverEaseWidth: 10,
            slackness: 0.9,
            stroke: {
                color: COLORS[strokeType][key],
                width: 2,
            },
            outlineStroke: {
                color: COLORS.outline[key],
                width: 1,
            },
        };
    }

    getEffectDependencies() {
        let sourcePoint = this.sourcePoint || { left: 0, top: 0 };
        if (typeof sourcePoint === "function") {
            sourcePoint = sourcePoint();
        }
        let targetPoint = this.targetPoint || { left: 0, top: 0 };
        if (typeof targetPoint === "function") {
            targetPoint = targetPoint();
        }
        const { x, y } = this.rootRef.el?.getBoundingClientRect() || { x: 0, y: 0 };

        return [
            this.rootRef.el,
            sourcePoint.left - x,
            sourcePoint.top - y,
            targetPoint.left - x,
            targetPoint.top - y,
            this.displayButtons,
        ];
    }


    getLinearInterpolation(startingPoint, endingPoint, lambda = 0.5) {
        return {
            left: lambda * startingPoint.left + (1 - lambda) * endingPoint.left,
            top: lambda * startingPoint.top + (1 - lambda) * endingPoint.top,
        };
    }

    getPathInfo(sourcePoint, targetPoint, slackness) {
        const xDelta = targetPoint.left - sourcePoint.left;
        const yDelta = targetPoint.top - sourcePoint.top;
        const directionFactor = Math.sign(xDelta);

        const xInc = 100 + (Math.abs(xDelta) * slackness) / 10;
        const yInc =
            Math.abs(yDelta) < 16 && directionFactor === -1 ? 15 - 0.001 * xDelta * slackness : 0;

        const b = {
            left: sourcePoint.left + xInc,
            top: sourcePoint.top + yInc,
        };

        const c = {
            left: targetPoint.left + (this.isNew && directionFactor === -1 ? xInc : -xInc),
            top: targetPoint.top + yInc,
        };

        const e = this.getLinearInterpolation(sourcePoint, b);
        const f = this.getLinearInterpolation(b, c);
        const g = this.getLinearInterpolation(c, targetPoint);
        const h = this.getLinearInterpolation(e, f);
        const i = this.getLinearInterpolation(f, g);
        const j = this.getLinearInterpolation(h, i);

        return {
            sourceControlPoint: b,
            targetControlPoint: c,
            removeButtonPosition: j,
        };
    }

    onLeftButtonClick() {
        if (this.props.onLeftButtonClick) {
            this.props.onLeftButtonClick();
        }
    }

    onRemoveButtonClick() {
        if (this.props.onRemoveButtonClick) {
            this.props.onRemoveButtonClick();
        }
    }

    onRightButtonClick() {
        if (this.props.onRightButtonClick) {
            this.props.onRightButtonClick();
        }
    }

    onWillRender() {
        const key = this.highlighted ? "highlightedColor" : "color";
        this.style.stroke.color = COLORS[this.alert || "default"][key];
        this.style.outlineStroke.color = COLORS.outline[key];
    }
}
