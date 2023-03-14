import sys

# Type hints are not strict constraints, just hints aiming at finding a matching widget.
# Supports simple types (str, int, bool and 3-4 tuples for min/max/default /precision)

def opencue_render(
        str_arg: str,
        int_arg_no_default: int,
        int_arg_with_default: int=1,
        int_range: tuple=[0, 5, 2], #[min, max, default]
        float_arg: float=1.0,
        float_range: tuple=[0, 5, 2, 2], #[min, max, default, float precision (decimals)],
        bool_arg: bool=True,
        opencue_token_arg: str="#FRAME_START#", #must be string, gets hidden in UI
        ):
	...

if __name__ == "__main__":
	arguments = sys.argv[1:]
	opencue_render(*arguments)