import Image from "next/image";
import iconlight from "../../app/iconlight.png";
import icondark from "../../app/icondark.png";

const CueWebIcon = () => {
  return (
    <div>
      <Image className="hidden dark:block" src={icondark} alt="dark-mode-image" height={70} />
      <Image className="mb-4 block dark:hidden" src={iconlight} alt="light-mode-image" height={70} />
    </div>
  );
};

export default CueWebIcon;
