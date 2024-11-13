import { Row } from "@tanstack/react-table";
import { MouseEvent, useEffect, useRef, useState } from "react";

export interface ContextMenuState {
  // Whether the context menu should be visible or not
  isVisible: boolean;
  // Position where the context menu should appear
  position: { x: number; y: number };
  // Row that is right-clicked on
  row: Row<any> | null; 
}

export interface MenuItem {
  // Label of the menu item
  label: string; 
  // Function that will execute after clicking on the menu item
  onClick(row: Row<any> | null): any;
  // Boolean that states whether the menu item should be active (clickable) or inactive
  isActive: boolean;
  // Component that contains a unique component/image for the menu item
  component?: React.ReactNode;
}

// Manages the context menu state, positioning, and visibility
export const useContextMenu = (contextMenuTargetAreaRef: React.RefObject<HTMLDivElement>) => {
  const contextMenuRef = useRef<HTMLDivElement>(null);
  const dialogOffsetRef = useRef<{ top: number; left: number; scrollLeft: number; scrollTop: number }>({
    top: 0,
    left: 0,
    scrollLeft: 0,
    scrollTop: 0,
  });

  const [contextMenuState, setContextMenuState] = useState<ContextMenuState>({
    isVisible: false,
    position: { x: 0, y: 0 },
    row: null,
  });

  // Adjusts the context menu position so that it:
  // - Stays within scrollable dialogs
  // - Doesn't overflow offscreen when near window edges
  const adjustMenuPosition = () => {
    if (!contextMenuRef.current) return;
    const { innerWidth, innerHeight } = window;
    const menuRect = contextMenuRef.current.getBoundingClientRect();
    if (!menuRect) return;
    let { x, y } = contextMenuState.position;

    const isInsideDialog = dialogOffsetRef.current.top !== 0 ||
                           dialogOffsetRef.current.left !== 0 ||
                           dialogOffsetRef.current.scrollLeft !== 0 ||
                           dialogOffsetRef.current.scrollTop !== 0;

    if (isInsideDialog) {
      x = x - dialogOffsetRef.current.left + dialogOffsetRef.current.scrollLeft;
      y = y - dialogOffsetRef.current.top + dialogOffsetRef.current.scrollTop;
    } else {
      // Adjust if overflowing right or bottom edges
      if (x + menuRect.width > innerWidth) {
        x = innerWidth - menuRect.width;
      }
      if (y + menuRect.height > innerHeight) {
        y = innerHeight - menuRect.height;
      }
    }

    setContextMenuState((prev) => ({
      ...prev,
      position: { x, y }, 
    }));
  };

  useEffect(() => {
    if (contextMenuState.isVisible) {
      adjustMenuPosition();
    }
  }, [contextMenuState.isVisible]);

  const contextMenuHandleOpen = (event: MouseEvent, row: Row<any>) => {
    const isInteractable = contextMenuTargetAreaRef.current && getComputedStyle(contextMenuTargetAreaRef.current).pointerEvents !== "none";
    if (!isInteractable || !event || !row) return;

    event.preventDefault();
    event.stopPropagation();

    const dialog = event.currentTarget.closest("[role='dialog']");
    if (dialog) {
      const rect = dialog.getBoundingClientRect();
      if (!rect) return;
      dialogOffsetRef.current = {
        top: rect.top,
        left: rect.left,
        scrollLeft: dialog.scrollLeft,
        scrollTop: dialog.scrollTop,
      };
    }

    setContextMenuState({
      isVisible: true,
      position: { x: event.clientX, y: event.clientY },
      row,
    });
  };

  const contextMenuHandleClose = () => {
    setContextMenuState((prev) => ({ ...prev, isVisible: false }));
  };

  const handleClickOutside = (event: globalThis.MouseEvent) => {
    if (contextMenuRef.current && !contextMenuRef.current.contains(event.target as Node)) {
      event.preventDefault();
      contextMenuHandleClose();
    }
  };

  useEffect(() => {
    if (contextMenuState.isVisible) {
      document.addEventListener("mousedown", handleClickOutside);
    } else {
      document.removeEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [contextMenuState.isVisible]);

  return { contextMenuState, contextMenuHandleOpen, contextMenuHandleClose, contextMenuRef, contextMenuTargetAreaRef };
};
