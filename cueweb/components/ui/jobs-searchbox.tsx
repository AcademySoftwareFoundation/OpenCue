import { styled, TextField, Tooltip, TooltipProps, Typography } from "@mui/material";
import { useTheme } from "next-themes";
import React, { useCallback, useState } from "react";
import { handleError } from "@/app/utils/notify_utils";

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
