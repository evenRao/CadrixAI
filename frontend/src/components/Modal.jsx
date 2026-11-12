import React, { useEffect, useRef } from "react";
import Icon from "./Icon.jsx";

export default function Modal({ title, onClose, children, wide = false }) {
  const ref = useRef(null);
  useEffect(() => {
    const dialog = ref.current;
    dialog.showModal();
    return () => dialog.close();
  }, []);
  return (
    <dialog ref={ref} className={`modal ${wide ? "modal-wide" : ""}`} aria-labelledby="modal-title" onCancel={onClose} onClick={(event) => { if (event.target === ref.current) { const box = ref.current.getBoundingClientRect(); if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) onClose(); } }}>
      <div className="modal-heading"><h2 id="modal-title">{title}</h2><button className="icon-button" aria-label={`Close ${title.toLowerCase()}`} onClick={onClose}><Icon name="close" /></button></div>
      <div className="modal-content">{children}</div>
    </dialog>
  );
}
