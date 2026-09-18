/** The ambient ground: blurred orbs under a veil, with film grain over both. */
export function Wash() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden>
      <div className="hg-orb hg-orb-a -left-[10%] top-[-12%] h-[70vh] w-[55vw]" />
      <div className="hg-orb hg-orb-b left-[30%] top-[20%] h-[65vh] w-[50vw]" />
      <div className="hg-orb hg-orb-c right-[-8%] top-[-6%] h-[72vh] w-[48vw]" />
      <div className="hg-veil absolute inset-0" />
      <div className="hg-grain absolute inset-0" />
    </div>
  );
}
