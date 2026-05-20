import Image from "next/image";
import iconlight from "../../app/iconlight.png";
import icondark from "../../app/icondark.png";

interface CueWebIconProps {
  height?: number;
}

const CueWebIcon = ({ height = 70 }: CueWebIconProps) => {
  return (
    <div>
      <Image className="hidden dark:block" src={icondark} alt="dark-mode-image" height={height} />
      <Image className="mb-4 block dark:hidden" src={iconlight} alt="light-mode-image" height={height} />
    </div>
  );
};

export default CueWebIcon;
