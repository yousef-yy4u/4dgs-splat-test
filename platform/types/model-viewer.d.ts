import "react";

// Minimal typing for the <model-viewer> web component (loaded from CDN).
declare module "react" {
  namespace JSX {
    interface IntrinsicElements {
      "model-viewer": React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & {
          src?: string;
          "ios-src"?: string;
          poster?: string;
          alt?: string;
          ar?: boolean;
          "ar-modes"?: string;
          "ar-scale"?: string;
          "camera-controls"?: boolean;
          "auto-rotate"?: boolean;
          "shadow-intensity"?: string;
          "touch-action"?: string;
          exposure?: string;
          autoplay?: boolean;
          "animation-name"?: string;
        },
        HTMLElement
      >;
    }
  }
}
