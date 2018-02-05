import { Directive, HostListener, ElementRef, OnInit, Input } from '@angular/core';
import { isNumber } from 'lodash';

@Directive({
  selector: '[decimalInput]'
})
export class DecimalInputDirective {

  private el: HTMLInputElement;

  constructor(private elementRef: ElementRef) {
    this.el = this.elementRef.nativeElement;
  }

  ngAfterContentChecked() {
    this.formatInput();
  }

  formatInput() {
    if(this.el.value.length > 0) {
      this.el.size = this.el.value.length;
    }

    // Set background if invalid value
    if (!isNumber(+this.el.value)) {
      this.el.style.borderBottom = 'solid 2px red';
      this.el.style.boxShadow = 'none';
    }
    else {
      this.el.style.borderBottom = '1px solid #808080';
      this.el.style.boxShadow = '0 -1px 0 #303030 inset'
    }

  }

}