"use client";

/*
 * Copyright Contributors to the OpenCue Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */


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

  // Cap the menu's height so it never extends past the viewport. The cap
  // is the smaller of "remaining space from click point to bottom of
  // viewport" minus a small margin, and 80vh as an upper bound. When the
  // content exceeds the cap, the menu scrolls internally via the
  // overflowY:'auto' rule below. This avoids the user having to zoom
  // out the browser to reach items that fell off screen on jobs with
  // the full ~25-item menu.
  //
  // No 240px floor: when the click lands near the bottom of the
  // When the click lands near the bottom of the viewport, the remaining
  // space below the cursor can be only a few pixels (or even negative),
  // which would make `min(80vh, 0px)` collapse the menu to zero height
  // and hide it entirely. Floor the value to MIN_MENU_HEIGHT_PX so the
  // internal scroll always has at least a few items visible - the
  // position-flip logic above already keeps the menu inside the viewport.
  const VIEWPORT_MARGIN_PX = 16;
  const MIN_MENU_HEIGHT_PX = 160;
  const remainingBelow =
    typeof window !== "undefined"
      ? window.innerHeight - contextMenuState.position.y - VIEWPORT_MARGIN_PX
      : 480;
  const menuMaxHeight = `min(80vh, ${Math.max(remainingBelow, MIN_MENU_HEIGHT_PX)}px)`;

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
        maxHeight: menuMaxHeight,
        overflowY: 'auto',
      }}
    >
      <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {items.map((item, index) => (
          <li key={index}>
            {item.separator ? (
              // Horizontal divider between logical groups (CueGUI parity).
              <hr
                style={{
                  margin: '4px 6px',
                  border: 0,
                  borderTop: '1px solid #e2e8f0',
                }}
              />
            ) : item.isActive ? (
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
