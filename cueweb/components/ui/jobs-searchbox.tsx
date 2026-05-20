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

import { styled, TextField, Tooltip, TooltipProps, Typography } from "@mui/material";
import { useTheme } from "next-themes";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { handleError } from "@/app/utils/notify_utils";
import { CUEWEB_FOCUS_SEARCH_EVENT } from "@/components/ui/shortcuts-overlay";

interface SearchboxProps {
  searchQuery: string;
  handleInputChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
  tooltipTitle: string;
  hidden: boolean;
}

// Styled tooltip component to customize its appearance
const StyledTooltip = styled(({ className, ...props }: TooltipProps & { className?: string }) => (
  <Tooltip {...props} classes={{ popper: className }} />
))(({ theme }) => ({
  [`& .MuiTooltip-tooltip`]: {
    maxWidth: "none",
    backgroundColor: theme.palette.background.paper,
    color: theme.palette.text.primary,
    boxShadow: theme.shadows[1],
  },
}));

// Searchbox component with tooltip for job search
const Searchbox: React.FC<SearchboxProps> = ({ searchQuery, handleInputChange, tooltipTitle, hidden }) => {
  const { theme } = useTheme();
  const [open, setOpen] = useState<boolean>(false);
  // Used by the global `/` shortcut to focus the search input. We hold a ref
  // to the underlying <input> so KeyboardShortcuts can fire a CustomEvent
  // and this component will move focus without prop drilling.
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Listen for the global "focus search" CustomEvent fired when the user
  // presses `/`. Defined here so the focus call stays scoped to the actual
  // input element this component owns.
  useEffect(() => {
    const handler = () => {
      inputRef.current?.focus();
      // Move the caret to the end if there's existing text so the user can
      // keep typing without their next keystroke selecting+replacing.
      inputRef.current?.setSelectionRange(
        inputRef.current.value.length,
        inputRef.current.value.length,
      );
    };
    window.addEventListener(CUEWEB_FOCUS_SEARCH_EVENT, handler);
    return () => window.removeEventListener(CUEWEB_FOCUS_SEARCH_EVENT, handler);
  }, []);

  // Handle focus event to close tooltip
  const handleFocus = useCallback(() => {
    setOpen(false);
  }, []);

  // Handle input change event to update search query and close tooltip
  const handleChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      try {
        setOpen(false);
        handleInputChange(event);
      } catch (error) {
        handleError(error, "Error handling input change");
      }
    },
    [handleInputChange],
  );

  // Handle mouse over event to show tooltip if not hidden
  const handleMouseOver = useCallback(() => {
    if (!hidden) {
      setOpen(true);
    }
  }, [hidden]);

  // Handle mouse leave event to close tooltip
  const handleMouseLeave = useCallback(() => {
    setOpen(false);
  }, []);

  return (
    <div onMouseOver={handleMouseOver} onMouseLeave={handleMouseLeave}>
      <StyledTooltip
        placement="bottom-start"
        title={
          <Typography component="span" variant="body2">
            <div dangerouslySetInnerHTML={{ __html: tooltipTitle }} />
          </Typography>
        }
        open={open}
      >
        <TextField
          variant="outlined"
          value={searchQuery}
          onChange={handleChange}
          placeholder="Search Jobs: add '!' after queries for regex"
          size="small"
          autoComplete="off"
          inputRef={inputRef}
          // Stable hook for the global `/` shortcut handler to locate this
          // input element via document.querySelector if a ref ever fails to
          // mount (defensive; the inputRef above is the primary path).
          inputProps={{ "data-cueweb-search-input": "true" }}
          sx={{
            mb: 2,
            width: "100%",
            backgroundColor: theme => theme.palette.background.default,
            color: theme => theme.palette.text.primary
          }}
          onFocus={handleFocus}
          onClick={handleFocus}
        />
      </StyledTooltip>
    </div>
  );
};

export default Searchbox;
