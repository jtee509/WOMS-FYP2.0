import { useRef, useEffect } from 'react';
import * as d3 from 'd3';

/**
 * Custom hook for integrating D3.js with React using the useRef pattern.
 *
 * Attaches D3 to a real DOM element via ref, preventing conflicts with
 * React's virtual DOM. The render callback receives a D3 selection of
 * the SVG element and runs inside useEffect.
 *
 * Usage:
 *   const svgRef = useD3((svg) => {
 *     svg.append('circle').attr('r', 50).attr('fill', 'blue');
 *   }, [data]);
 *
 *   return <svg ref={svgRef} />;
 */
export function useD3(
  renderFn: (svg: d3.Selection<SVGSVGElement, unknown, null, undefined>) => void,
  dependencies: unknown[],
): React.RefObject<SVGSVGElement | null> {
  const ref = useRef<SVGSVGElement | null>(null);

  useEffect(() => {
    if (ref.current) {
      const svg = d3.select(ref.current);
      renderFn(svg);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies);

  return ref;
}
