
const colors = {
    primary: '#3d4449',
    focus: '#303030',
    hover: '#303030',
    selected: 'white',
    unselected: '#b3b3b3',
    dropdownIndicator: '#F1CA57'
  };

  export const SelectStyles = {
    control: (provided, state) => ({
      ...provided,
      width: '100%',
      height: '40px',
      backgroundColor: colors.primary,
      // borderColor: state.isFocused ? colors.focus : colors.focus,
      boxShadow: state.isFocused ? '0 0 0 1px #F1CA57' : 'none',
      border: state.isFocused ? "none" : "none",
      // color: colors.selected,
      // '&:hover': {
      //     borderColor: colors.hover
      // },
      outline: 'none'
  }),
    option: (provided, state) => ({
        ...provided,
        backgroundColor: state.isFocused ? colors.focus : colors.focus,
        color: state.isSelected ? colors.selected : colors.unselected,
        '&:hover': {
            backgroundColor: colors.hover
        },
        textAlign: 'left'
    }),
    input: (provided, state) => ({
        ...provided,
        color: colors.selected,
        boxShadow: state.isFocused ? 'none' : 'none',
        outline: 'none'
    }),
    singleValue: (provided) => ({
        ...provided,
        color: colors.selected
    }),
    placeholder: (provided) => ({
        ...provided,
        color: colors.unselected
    }),
    indicatorSeparator: (provided) => ({
        ...provided,
        backgroundColor: 'transparent'
    }),
    dropdownIndicator: (provided) => ({
        ...provided,
        color: colors.dropdownIndicator
    }),
    menu: (provided) => ({
        ...provided,
        backgroundColor: colors.focus,
        boxShadow : 'none',
        outline: 'none'
    })
  };