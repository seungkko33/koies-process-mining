import type { DFGEdge } from "../../types/dfg";

const integerFormatter = new Intl.NumberFormat("ko-KR");

interface ProcessMapTableProps {
  edges: DFGEdge[];
}

export function ProcessMapTable({ edges }: ProcessMapTableProps) {
  return (
    <div className="transition-table-wrap">
      <table className="transition-table">
        <caption>현재 threshold를 통과한 transition</caption>
        <thead>
          <tr><th>Source</th><th>Target</th><th>Transitions</th><th>Cases</th></tr>
        </thead>
        <tbody>
          {edges.map((edge) => (
            <tr key={`${edge.source}\u0000${edge.target}`}>
              <td>{edge.source}</td>
              <td>{edge.target}</td>
              <td>{integerFormatter.format(edge.transition_count)}</td>
              <td>{integerFormatter.format(edge.case_count)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

