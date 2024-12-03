import * as React from "react";
import * as LabelPrimitive from "@radix-ui/react-label";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const getLabelVariants = () => {
  // cva or Class Variance Authority is a helper function that facilitates the design of a componenet.
  // It takes in styles assigned using className, along with a second optional argument: any variant configurations
  const variants = cva("text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70");
  if (!variants) {
    // Handle the case when the variants object is not valid
    throw new Error("Failed to retrieve label variants.");
  }
  return variants;
};

const Label = React.forwardRef<
  React.ElementRef<typeof LabelPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root> & VariantProps<ReturnType<typeof getLabelVariants>>
>(({ className, ...props }, ref) => {
  let variants;
  try {
    variants = getLabelVariants();
  } catch (error) {
    console.error("Error retrieving label variants:", error);
    variants = {}; // Provide an empty object as a default value
  }

  // Proceed with rendering, ensuring variants is always defined
  return <LabelPrimitive.Root ref={ref} className={cn(variants, className)} {...props} />;
});
Label.displayName = LabelPrimitive.Root.displayName;

export { Label };
