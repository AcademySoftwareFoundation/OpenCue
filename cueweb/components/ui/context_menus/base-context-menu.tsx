"use client";

import * as React from "react";
import { ContextMenuState, MenuItem } from "./useContextMenu";

interface BaseContextMenuProps {
  items: MenuItem[];
  contextMenuState: ContextMenuState;
  contextMenuHandleClose: () => void;
  contextMenuRef: React.RefObject<HTMLDivElement>;
  contextMenuTargetAreaRef: React.RefObject<HTMLDivElement>;
}

// The base context menu component that includes styling for the menu and each menu item
export const BaseContextMenu: React.FC<BaseContextMenuProps> = ({
  items,
  contextMenuState,
  contextMenuHandleClose,
  contextMenuRef,
  contextMenuTargetAreaRef,
}) => {
  if (!contextMenuState.isVisible || !contextMenuState.position) return null;

  // Event handlers for better performance and readability
  const handleItemClick = (item: MenuItem) => {
    item.onClick(contextMenuState.row);
    contextMenuHandleClose();
  };

  const handleMouseEnter = (e: React.MouseEvent<HTMLDivElement>) => {
    e.currentTarget.style.backgroundColor = "#e5e7eb";
  };

  const handleMouseLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    e.currentTarget.style.backgroundColor = "transparent";
  };

  return (
    <div
      ref={contextMenuRef}
      style={{
        position: 'fixed',
        top: contextMenuState.position.y,
        left: contextMenuState.position.x,
        zIndex: 2000,
        background: '#fff',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
        borderRadius: '4px',
        border: '1px solid #e2e8f0',
        padding: '4px',
        whiteSpace: 'nowrap',
      }}
    >
      <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {items.map((item, index) => (
          <li key={index}>
            {item.isActive ? (
              <div
                onClick={() => handleItemClick(item)}
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
                style={{
                  padding: '8px 12px',
                  fontSize: '14px',
                  color: '#374151',
                  cursor: 'pointer',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  transition: 'background-color 0.2s',
                }}
              >
                {item.component}
                {item.label}
              </div>
            ) : (
              <div
                style={{
                  padding: '8px 12px',
                  fontSize: '14px',
                  color: '#D3D3D3',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  pointerEvents: 'none',
                }}
              >
                {item.component}
                {item.label}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};
